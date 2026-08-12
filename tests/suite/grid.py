from typing import Any, Dict, Final

from sampletones_application.categories.elements.global_ import ContextElements
from sampletones_application.ui.panels.sequencer.grid.surface import BlockShortcuts, GridEditSurface
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId

CLIPBOARD_LABELS: Final[Dict[ContextElements, str]] = {
    ContextElements.COPY: "Copy",
    ContextElements.CUT: "Cut",
    ContextElements.PASTE: "Paste",
    ContextElements.DELETE: "Delete",
}

TRACKER_BLOCK_SHORTCUTS: Final[BlockShortcuts] = BlockShortcuts(
    copy=ShortcutId.TRACKER_COPY_BLOCK,
    cut=ShortcutId.TRACKER_CUT_BLOCK,
    paste=ShortcutId.TRACKER_PASTE_BLOCK,
)

ORDER_BLOCK_SHORTCUTS: Final[BlockShortcuts] = BlockShortcuts(
    copy=ShortcutId.ORDER_COPY_BLOCK,
    cut=ShortcutId.ORDER_CUT_BLOCK,
    paste=ShortcutId.ORDER_PASTE_BLOCK,
)


def attach_edit_surface(
    panel: Any,
    block_shortcuts: BlockShortcuts,
    target: Any,
) -> None:
    """Gives a hand-built grid panel the edit surface its menus and its cursor's target run through.

    A case that builds a panel without its constructor supplies the collaborators the panel would
    have composed, and this is the one that resolves a target and prints the clipboard items.
    """
    panel._surface = GridEditSurface(
        grid=panel,
        blocks=panel._blocks,
        target=target,
        shortcuts=panel._shortcuts,
        block_shortcuts=block_shortcuts,
        labels=CLIPBOARD_LABELS,
    )
