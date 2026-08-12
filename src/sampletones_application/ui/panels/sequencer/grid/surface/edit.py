from __future__ import annotations

from typing import Any, Callable, Generic, Mapping, Optional, TypeVar

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures, BlockTarget
from sampletones_application.ui.panels.sequencer.grid.surface.clipboard import BlockShortcuts, ClipboardItems
from sampletones_application.ui.panels.sequencer.grid.surface.protocol import EditGrid
from sampletones_application.ui.panels.sequencer.grid.surface.targets import CursorTargets, TargetFactory
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource

CursorT = TypeVar("CursorT")
RegionT = TypeVar("RegionT")
CellT = TypeVar("CellT")
TargetT = TypeVar("TargetT", bound=BlockTarget[Any, Any])


class GridEditSurface(Generic[CursorT, RegionT, CellT, TargetT]):
    """A sequencer grid as the menu bar's Edit menu and its own keys reach it.

    The menu bar asks the surface for the actions of whichever grid holds the cursor, and the
    surface asks that grid to build them for the target the cursor names. A key press acts on that
    same target, so one place resolves what the cursor stands on and every door agrees on it.

    Both grids reach the Edit menu through one implementation, so the menu states what the next key
    press would.
    """

    def __init__(
        self,
        *,
        grid: EditGrid[CursorT, RegionT, TargetT],
        targets: CursorTargets[CursorT, RegionT, TargetT],
        clipboard: ClipboardItems[RegionT, CellT],
        blocks: BlockGestures[RegionT, CellT],
    ) -> None:
        self._grid = grid
        self._targets = targets
        self._clipboard = clipboard
        self._blocks = blocks

    @classmethod
    def build(
        cls,
        *,
        grid: EditGrid[CursorT, RegionT, TargetT],
        blocks: BlockGestures[RegionT, CellT],
        target: TargetFactory[CursorT, RegionT, TargetT],
        shortcuts: ShortcutSource,
        block_shortcuts: BlockShortcuts,
        labels: Mapping[ContextElements, str],
    ) -> GridEditSurface[CursorT, RegionT, CellT, TargetT]:
        """Composes the surface a grid states itself through, from the parts that grid supplies.

        A grid names its own target type, the three keys its clipboard items print and the gestures
        its hooks answer; the collaborators built from those are the same in either grid.
        """
        return cls(
            grid=grid,
            targets=CursorTargets(
                state=grid.input_state,
                target=target,
            ),
            clipboard=ClipboardItems(
                blocks=blocks,
                shortcuts=shortcuts,
                block_shortcuts=block_shortcuts,
                labels=labels,
            ),
            blocks=blocks,
        )

    def owns_edit_actions(self) -> bool:
        """Whether the Edit menu states this grid's actions, which it does while the grid owns keys.

        The menu offers what the next press would reach, so one question decides both.
        """
        return self._grid.owns_keys()

    def build_edit_actions(self) -> None:
        """Builds the grid's whole action set for the cell the cursor stands on.

        The menu bar asks while the grid owns the editing gestures, so the cursor names the target
        the same way a pointer names it on the cell menu.
        """
        target = self.cursor_target()
        if target is not None:
            self._grid.add_action_items(target)

    def target_at(self, cell: CursorT) -> TargetT:
        """The cell a set of actions is raised on, paired with the block those actions act on."""
        return self._targets.at(cell)

    def cursor_target(self) -> Optional[TargetT]:
        """The target the cursor names, which is what a key press and the Edit menu act on."""
        return self._targets.at_cursor()

    def add_block_items(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Builds the clipboard items, acting on the block the actions were raised on."""
        self._clipboard.add_items(target)

    def copy(self) -> None:
        self._at_cursor(self._blocks.copy_at)

    def cut(self) -> None:
        self._at_cursor(self._blocks.cut_at)

    def delete(self) -> None:
        self._at_cursor(self._blocks.delete_at)

    def paste(self) -> None:
        self._at_cursor(self._blocks.paste_at)

    def _at_cursor(
        self,
        gesture: Callable[[BlockTarget[RegionT, CellT]], None],
    ) -> None:
        """Raises a gesture on the cell the cursor stands on, the entry being typed landing first.

        Committing ahead of the gesture is what lets a block carry the value the reader has just
        finished typing.
        """
        self._grid.commit_entry()
        target = self.cursor_target()
        if target is not None:
            gesture(target)
