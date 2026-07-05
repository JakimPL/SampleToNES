import contextlib
from typing import Iterator

import dearpygui.dearpygui as dpg

from sampletones_shared.types.callback import VoidCallback


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


def add_play_menu_item(label: str, on_play: VoidCallback) -> None:
    """Add the shared "Play" context-menu item; the caller supplies the play action.

    The samples panel and every file browser expose the same Play affordance over
    different sources (an in-memory sample, a reconstruction or audio file). Routing
    them all through one builder keeps the item from drifting apart across panels.
    """
    dpg.add_menu_item(label=label, callback=on_play)
