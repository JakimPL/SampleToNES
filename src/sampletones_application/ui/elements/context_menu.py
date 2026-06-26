import dearpygui.dearpygui as dpg

from sampletones_shared.types.callback import VoidCallback


def add_play_menu_item(label: str, on_play: VoidCallback) -> None:
    """Add the shared "Play" context-menu item; the caller supplies the play action.

    The samples panel and every file browser expose the same Play affordance over
    different sources (an in-memory sample, a reconstruction or audio file). Routing
    them all through one builder keeps the item from drifting apart across panels.
    """
    dpg.add_menu_item(label=label, callback=on_play)
