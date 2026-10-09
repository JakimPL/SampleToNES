from dataclasses import dataclass
from functools import partial
from typing import Dict, Final, Generic, Mapping, Tuple, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_application.categories.context import context_label
from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures, BlockTarget
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.application import Sender

RegionT = TypeVar("RegionT")
CellT = TypeVar("CellT")

CLIPBOARD_ACTIONS: Final[Tuple[ContextElements, ...]] = (
    ContextElements.COPY,
    ContextElements.CUT,
    ContextElements.PASTE,
    ContextElements.DELETE,
)


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


class ClipboardItems(Generic[RegionT, CellT]):
    """The four items every grid's menus print: copy, cut, paste and delete.

    The words come from the shared context vocabulary and the accelerators from the grid's own
    three bindings, so a grid states only which keys it answers to and the items read the same in
    either grid.
    """

    def __init__(
        self,
        *,
        blocks: BlockGestures[RegionT, CellT],
        shortcuts: ShortcutSource,
        block_shortcuts: BlockShortcuts,
        labels: Mapping[ContextElements, str],
    ) -> None:
        self._blocks = blocks
        self._shortcuts = shortcuts
        self._block_shortcuts = block_shortcuts
        self._labels = labels

    @staticmethod
    def labels(language_manager: LanguageManager) -> Dict[ContextElements, str]:
        """The words every clipboard item prints, read from the vocabulary each grid shares."""
        return {element: context_label(language_manager, element) for element in CLIPBOARD_ACTIONS}

    def add_items(self, target: BlockTarget[RegionT, CellT]) -> None:
        """Builds the four items, acting on the block the actions were raised on.

        Paste is offered on the block the clipboard last answered with, and the opening asks the
        clipboard again, so the item follows the fresh answer once it lands. It anchors at the
        target's own cell, so the cell menu lands a block where the pointer is while the keys land
        it under the cursor.
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
        paste = dpg.add_menu_item(
            label=self._labels[ContextElements.PASTE],
            shortcut=self._shortcuts.display(self._block_shortcuts.paste),
            enabled=self._blocks.can_paste(),
            callback=lambda: self._blocks.paste_at(target),
        )
        self._blocks.refresh_paste(partial(self._offer_paste, paste))
        dpg.add_menu_item(
            label=self._labels[ContextElements.DELETE],
            callback=lambda: self._blocks.delete_at(target),
        )

    def _offer_paste(self, item: Sender) -> None:
        """Sets the Paste item by the block the clipboard's fresh answer leaves in hand."""
        dpg_configure_item(item, enabled=self._blocks.can_paste())
