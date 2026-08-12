from dataclasses import dataclass
from typing import Callable, Final, List, Optional

from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures
from sampletones_application.ui.panels.sequencer.grid.surface.clipboard import ClipboardItems
from sampletones_application.ui.panels.sequencer.grid.surface.edit import GridEditSurface
from sampletones_application.ui.panels.sequencer.grid.surface.targets import CursorTargets
from sampletones_application.ui.panels.sequencer.input.state import GridInputState
from tests.suite.grid import CLIPBOARD_LABELS, TRACKER_BLOCK_SHORTCUTS
from tests.suite.shortcuts import shipped_source

CURSOR_CELL: Final[str] = "cursor cell"
CLICKED_CELL: Final[str] = "clicked cell"


@dataclass(frozen=True)
class Target:
    """The cell a set of actions was raised on, and the block those actions act on."""

    cell: str
    region: str

    @classmethod
    def at(cls, cell: str) -> "Target":
        """The target a cell resolves to, which is the pair the fake state states for it."""
        return cls(cell=cell, region=f"{cell} block")

    @property
    def anchor(self) -> str:
        return f"{self.cell} anchor"


@dataclass(frozen=True)
class State(GridInputState[str, str]):
    """A grid's state as the surface reads it: where the cursor stands, and what a cell falls in.

    A cell's own block reads as the cell it was bounded from, so a target names the cell that
    raised it and the block it resolved to in one readable pair.
    """

    def _region_between(self, first: str, _second: str) -> str:
        return f"{first} block"

    def _covers(self, region: str, cell: str) -> bool:
        return region == f"{cell} block"


CURSOR_TARGET: Final[Target] = Target.at(CURSOR_CELL)
CLICKED_TARGET: Final[Target] = Target.at(CLICKED_CELL)


class Grid:
    """A grid recording what it was asked to do, in the order it was asked.

    The entry it settles, the hooks it announces through and the action sets it was asked to build
    land in one list, so a case reads both what a gesture reached and when the grid committed what
    was being typed.
    """

    def __init__(
        self,
        *,
        cursor: Optional[str] = CURSOR_CELL,
        owns: bool = True,
        can_paste: bool = True,
    ) -> None:
        self.events: List[str] = []
        self.cursor = cursor
        self._owns = owns
        self.on_copy_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"copy {region}")
        self.on_cut_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"cut {region}")
        self.on_delete_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"delete {region}")
        self.on_paste_block: Optional[Callable[[str], None]] = lambda cell: self.events.append(f"paste {cell}")
        self.can_paste_block: Optional[Callable[[], bool]] = lambda: can_paste

    def owns_keys(self) -> bool:
        return self._owns

    def input_state(self) -> State:
        return State(cursor=self.cursor)

    def add_action_items(self, target: Target) -> None:
        self.events.append(f"actions {target.cell}")

    def commit_entry(self) -> None:
        self.events.append("commit")

    def cursor_targets(self) -> CursorTargets[str, str, Target]:
        """The target resolver over this grid, which is what each door asks for a cell's block."""
        return CursorTargets(state=self.input_state, target=Target)

    def clipboard_items(self) -> ClipboardItems[str, str]:
        """The four items over this grid, printing the tracker's own keys and stand-in words."""
        return ClipboardItems(
            blocks=BlockGestures(grid=self),
            shortcuts=shipped_source(),
            block_shortcuts=TRACKER_BLOCK_SHORTCUTS,
            labels=CLIPBOARD_LABELS,
        )

    def edit_surface(self) -> GridEditSurface[str, str, str, Target]:
        """The surface over this grid, composed from the collaborators a real panel supplies."""
        return GridEditSurface(
            grid=self,
            targets=self.cursor_targets(),
            clipboard=self.clipboard_items(),
            blocks=BlockGestures(grid=self),
        )
