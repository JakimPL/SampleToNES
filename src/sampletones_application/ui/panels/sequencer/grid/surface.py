from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, Generic, Mapping, Optional, Protocol, Tuple, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import context_label
from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures, BlockTarget
from sampletones_application.ui.panels.sequencer.input.state import GridInputState
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource

CursorT = TypeVar("CursorT")
RegionT = TypeVar("RegionT")
CellT = TypeVar("CellT")
TargetT = TypeVar("TargetT", bound=BlockTarget[Any, Any])
TargetT_co = TypeVar("TargetT_co", covariant=True)
TargetT_contra = TypeVar("TargetT_contra", contravariant=True)
CursorT_contra = TypeVar("CursorT_contra", contravariant=True)
RegionT_contra = TypeVar("RegionT_contra", contravariant=True)

CLIPBOARD_ACTIONS: Final[Tuple[ContextElements, ...]] = (
    ContextElements.COPY,
    ContextElements.CUT,
    ContextElements.PASTE,
    ContextElements.DELETE,
)


def clipboard_labels(language_manager: LanguageManager) -> Dict[ContextElements, str]:
    """The words every clipboard item prints, read from the vocabulary each grid shares."""
    return {element: context_label(language_manager, element) for element in CLIPBOARD_ACTIONS}


@dataclass(frozen=True)
class BlockShortcuts:
    """The keys one grid answers the clipboard gestures with.

    Delete stands apart from the three: ``Del`` empties a selection while one stands and clears the
    cell under the cursor otherwise, so the grid resolves it from the selection and its item prints
    no key.
    """

    copy: ShortcutId
    cut: ShortcutId
    paste: ShortcutId


class TargetFactory(Protocol[CursorT_contra, RegionT_contra, TargetT_co]):
    """How a grid's own target is built from the pair every target carries."""

    def __call__(self, *, cell: CursorT_contra, region: RegionT_contra) -> TargetT_co: ...


class EditGrid(Protocol[CursorT, RegionT, TargetT_contra]):
    """What a grid states to the edit surface built over it.

    The state carries the cursor and the selection a target is resolved from, and the grid states
    its own actions for a target the surface hands back. Whether the grid owns those gestures at
    this moment is the question its key scope already answers, so one predicate serves the keyboard
    and the menu alike.
    """

    def owns_keys(self) -> bool: ...

    def input_state(self) -> GridInputState[CursorT, RegionT]: ...

    def add_action_items(self, target: TargetT_contra) -> None: ...

    def commit_entry(self) -> None:
        """Writes the entry being typed into the cell the cursor stands on."""


class GridEditSurface(Generic[CursorT, RegionT, CellT, TargetT]):
    """A sequencer grid as the menu bar's Edit menu reaches it.

    The menu bar asks the surface for the actions of whichever grid holds the cursor, and the
    surface asks that grid to build them for the target the cursor names. Both grids reach the
    Edit menu through one implementation, so the menu states what the next key press would.

    It also prints the clipboard four, which are the actions every grid carries: the words come
    from the shared context vocabulary and the accelerators from the grid's own three bindings, so
    a grid states only which keys it answers to and the items read the same in either.
    """

    def __init__(
        self,
        *,
        grid: EditGrid[CursorT, RegionT, TargetT],
        blocks: BlockGestures[RegionT, CellT],
        target: TargetFactory[CursorT, RegionT, TargetT],
        shortcuts: ShortcutSource,
        block_shortcuts: BlockShortcuts,
        labels: Mapping[ContextElements, str],
    ) -> None:
        self._grid = grid
        self._blocks = blocks
        self._target = target
        self._shortcuts = shortcuts
        self._block_shortcuts = block_shortcuts
        self._labels = labels

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
        """The cell a set of actions is raised on, paired with the block those actions act on.

        The block is the selection the cell falls inside, or the cell alone, so a menu raised
        within a selection reaches the whole of it and one raised elsewhere reaches what it names.
        """
        return self._target(
            cell=cell,
            region=self._grid.input_state().region_at(cell),
        )

    def cursor_target(self) -> Optional[TargetT]:
        """The target the cursor names, which is what a key press and the Edit menu act on."""
        cursor = self._grid.input_state().cursor
        if cursor is None:
            return None

        return self.target_at(cursor)

    def copy(self) -> None:
        self._at_cursor(self._blocks.copy_at)

    def cut(self) -> None:
        self._at_cursor(self._blocks.cut_at)

    def delete(self) -> None:
        self._at_cursor(self._blocks.delete_at)

    def paste(self) -> None:
        self._at_cursor(self._blocks.paste_at)

    def can_paste(self) -> bool:
        """Whether a block stands ready for a paste to write."""
        return self._blocks.can_paste()

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

    def add_block_items(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Builds the clipboard items, acting on the block the actions were raised on.

        Paste is offered once a block has been copied, and it anchors at the target's own cell, so
        the cell menu lands a block where the pointer is while the keys land it under the cursor.
        """
        dpg.add_menu_item(
            label=self._labels[ContextElements.COPY],
            shortcut=self._shortcuts.display(self._block_shortcuts.copy),
            callback=lambda: self._blocks.copy_at(target),
        )
        dpg.add_menu_item(
            label=self._labels[ContextElements.CUT],
            shortcut=self._shortcuts.display(self._block_shortcuts.cut),
            callback=lambda: self._blocks.cut_at(target),
        )
        dpg.add_menu_item(
            label=self._labels[ContextElements.PASTE],
            shortcut=self._shortcuts.display(self._block_shortcuts.paste),
            enabled=self._blocks.can_paste(),
            callback=lambda: self._blocks.paste_at(target),
        )
        dpg.add_menu_item(
            label=self._labels[ContextElements.DELETE],
            callback=lambda: self._blocks.delete_at(target),
        )
