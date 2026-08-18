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

    The hooks are the grid's own, so the coordinator keeps wiring them where it already does.
    """

    on_copy_block: Optional[Callable[[RegionT], None]]
    on_cut_block: Optional[Callable[[RegionT], None]]
    on_delete_block: Optional[Callable[[RegionT], None]]
    on_paste_block: Optional[Callable[[CellT], None]]
    can_paste_block: Optional[Callable[[], bool]]


class BlockGestures(CallbackMixin, Generic[RegionT, CellT]):
    """The four gestures a grid's blocks answer to: copy, cut, paste and delete.

    Three doors raise the same four, and each names the target it acts on: a cell menu and the menu
    bar's Edit menu name the target they were built for, and a key press names the cursor's.
    Holding the four here is what has every door fire one implementation.
    """

    def __init__(self, *, grid: BlockGrid[RegionT, CellT]) -> None:
        self._grid = grid

    def can_paste(self) -> bool:
        """Whether a block stands ready for a paste to write."""
        return self.query(self._grid.can_paste_block, default=False)

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
