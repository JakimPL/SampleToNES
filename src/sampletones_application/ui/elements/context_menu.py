import contextlib
from pathlib import Path
from typing import Iterator, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.tooltip import show_tooltip
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.system.paths import open_path_in_explorer


@contextlib.contextmanager
def context_menu() -> Iterator[None]:
    """Open the standard right-click popup window that hosts context-menu items.

    Every panel's context menu shares this popup style, so routing them through one
    builder keeps them from drifting apart.
    """
    with dpg.window(
        popup=True,
        no_move=True,
        no_resize=True,
        no_title_bar=True,
        min_size=(0, 0),
        modal=False,
    ):
        yield


def add_play_menu_item(
    label: str,
    on_play: VoidCallback,
    shortcut: str = "",
) -> None:
    """Add the shared "Play" context-menu item; the caller supplies the play action.

    The samples panel and every file browser expose the same Play affordance over
    different sources (an in-memory sample, a reconstruction or audio file). Routing
    them all through one builder keeps the item from drifting apart across panels.

    ``shortcut`` is shown as the item's accelerator hint when the action has a bound key,
    and left blank for sources reached only by clicking.
    """
    dpg.add_menu_item(
        label=label,
        shortcut=shortcut,
        callback=on_play,
    )


def add_detail_items(
    items: Sequence[Tuple[str, str]],
    *,
    color: BaseColor,
    tooltip: Optional[str] = None,
) -> None:
    """Add a block of read-only ``label: value`` lines to the context menu being built.

    A menu states what its target is alongside what can be done to it: a file browser prints the
    settings a reconstruction was made with, and the samples menu prints the bytes a sample
    occupies. Both read as the same tinted, monospaced block under a separator of its own, so the
    facts stay apart from the items a reader clicks.

    Args:
        items: The label and value of each line, in the order the menu prints them.
        color: The tint the lines take, which marks them as facts rather than actions.
        tooltip: An explanation the whole block shares, reached by hovering any of its lines.
    """
    if not items:
        return

    dpg.add_separator()
    for label, value in items:
        detail_text = dpg.add_text(f"{label}: {value}")
        dpg_set_palette_color(detail_text, color)
        FontRegistry.bind_to_item(detail_text, Font.MONO_SMALL)
        if tooltip is not None:
            show_tooltip(detail_text, tooltip)


def add_path_menu_items(
    language_manager: LanguageManager,
    path: Path,
) -> None:
    """Add the shared block of filesystem actions for ``path`` to the context menu being built.

    Every menu naming something on disk offers the same three: the name and the full path to the
    clipboard, and the file revealed in the file manager. Routing the file browsers and the
    converter's gathered recordings through one builder keeps them reading alike.
    """
    dpg.add_separator()
    dpg.add_menu_item(
        label=language_manager["global.context.label.copy_filename"],
        callback=lambda: dpg.set_clipboard_text(str(path.name)),
    )
    dpg.add_menu_item(
        label=language_manager["global.context.label.copy_path"],
        callback=lambda: dpg.set_clipboard_text(str(path)),
    )
    dpg.add_menu_item(
        label=language_manager["global.context.label.open_in_explorer"],
        callback=lambda: open_path_in_explorer(path),
    )
