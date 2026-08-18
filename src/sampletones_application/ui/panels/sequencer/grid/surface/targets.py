from typing import Any, Callable, Generic, Optional, Protocol, TypeVar

from sampletones_application.ui.panels.sequencer.grid.gestures import BlockTarget
from sampletones_application.ui.panels.sequencer.input.state import GridInputState

CursorT = TypeVar("CursorT")
RegionT = TypeVar("RegionT")
TargetT = TypeVar("TargetT", bound=BlockTarget[Any, Any])
TargetT_co = TypeVar("TargetT_co", covariant=True)
CursorT_contra = TypeVar("CursorT_contra", contravariant=True)
RegionT_contra = TypeVar("RegionT_contra", contravariant=True)


class TargetFactory(Protocol[CursorT_contra, RegionT_contra, TargetT_co]):
    """How a grid's own target is built from the pair every target carries."""

    def __call__(self, *, cell: CursorT_contra, region: RegionT_contra) -> TargetT_co: ...


class CursorTargets(Generic[CursorT, RegionT, TargetT]):
    """Which block a cell reaches, in the grid whose state names the selection.

    Every door raises its actions on a target, and all three resolve one the same way: the cell is
    paired with the block it falls inside. Reading the state afresh on each call is what keeps the
    pair current, since a grid rebinds a frozen state on every edit.
    """

    def __init__(
        self,
        *,
        state: Callable[[], GridInputState[CursorT, RegionT]],
        target: TargetFactory[CursorT, RegionT, TargetT],
    ) -> None:
        self._state = state
        self._target = target

    def at(self, cell: CursorT) -> TargetT:
        """The cell a set of actions is raised on, paired with the block those actions act on.

        The block is the selection the cell falls inside, or the cell alone, so a menu raised
        within a selection reaches the whole of it and one raised elsewhere reaches what it names.
        """
        return self._target(
            cell=cell,
            region=self._state().region_at(cell),
        )

    def at_cursor(self) -> Optional[TargetT]:
        """The target the cursor names, which is what a key press and the Edit menu act on."""
        cursor = self._state().cursor
        if cursor is None:
            return None

        return self.at(cursor)
