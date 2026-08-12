from typing import Callable, Generic, Optional, Protocol, TypeVar

from sampletones_shared.utils.callbacks import CallbackMixin

RegionT = TypeVar("RegionT")
CellT = TypeVar("CellT")
RegionT_co = TypeVar("RegionT_co", covariant=True)
CellT_co = TypeVar("CellT_co", covariant=True)


class BlockTarget(Protocol[RegionT_co, CellT_co]):
    """What a block gesture acts on: the block it covers, and the cell a pasted block lands at.

    A grid resolves one from whichever cell raised the gesture, so the pair travels together and
    each gesture reads the half it acts on.
    """

    @property
    def region(self) -> RegionT_co: ...

    @property
    def anchor(self) -> CellT_co: ...


class BlockGrid(Protocol[RegionT, CellT]):
    """What a grid states to the block gestures raised over it.

    The hooks are the grid's own, so the coordinator keeps wiring them where it already does; the
    two methods are what a key press needs, since it names its target through the cursor.
    """

    on_copy_block: Optional[Callable[[RegionT], None]]
    on_cut_block: Optional[Callable[[RegionT], None]]
    on_delete_block: Optional[Callable[[RegionT], None]]
    on_paste_block: Optional[Callable[[CellT], None]]
    can_paste_block: Optional[Callable[[], bool]]

    def commit_entry(self) -> None:
        """Writes the entry being typed into the cell the cursor stands on."""

    def cursor_target(self) -> Optional[BlockTarget[RegionT, CellT]]:
        """The target the cursor names, once the grid holds a cursor."""


class BlockGestures(CallbackMixin, Generic[RegionT, CellT]):
    """The four gestures a grid's blocks answer to: copy, cut, paste and delete.

    Three doors raise the same four. A key press acts at the cursor, and takes its target once the
    entry being typed has landed, so a gesture carries the value the reader has just finished. A
    cell menu and the menu bar's Edit menu each name the target they were built for and act on it
    where it stands. Holding the four here is what has every door fire one implementation.

    The plain gestures act at the cursor; the ``_at`` gestures act on a target already named.
    """

    def __init__(self, *, grid: BlockGrid[RegionT, CellT]) -> None:
        self._grid = grid

    def can_paste(self) -> bool:
        """Whether a block stands ready for a paste to write."""
        return self.query(self._grid.can_paste_block, default=False)

    def copy(self) -> None:
        self._at_cursor(self.copy_at)

    def cut(self) -> None:
        self._at_cursor(self.cut_at)

    def delete(self) -> None:
        self._at_cursor(self.delete_at)

    def paste(self) -> None:
        self._at_cursor(self.paste_at)

    def copy_at(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Takes what a target covers, leaving the grid as it stands."""
        self.call(self._grid.on_copy_block, target.region)

    def cut_at(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Takes what a target covers, and empties it."""
        self.call(self._grid.on_cut_block, target.region)

    def delete_at(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Empties what a target covers, the block in hand standing as it is."""
        self.call(self._grid.on_delete_block, target.region)

    def paste_at(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Writes the block in hand from a target's own cell, which is where it lands."""
        self.call(self._grid.on_paste_block, target.anchor)

    def _at_cursor(
        self,
        gesture: Callable[[BlockTarget[RegionT, CellT]], None],
    ) -> None:
        """Raises a gesture on the cell the cursor stands on, the entry being typed landing first.

        Committing ahead of the gesture is what lets a block carry the value the reader has just
        finished typing.
        """
        self._grid.commit_entry()
        target = self._grid.cursor_target()
        if target is not None:
            gesture(target)
