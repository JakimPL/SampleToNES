from contextlib import contextmanager
from typing import Iterator

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_THEME_PANEL_GROUND
from sampletones_application.ui.themes.registry import ThemeRegistry


@contextmanager
def well(
    parent: str,
    tag: str,
    *,
    height: int = 0,
    show: bool = True,
) -> Iterator[str]:
    """Open a recessed region inside a card and bind its depth theme.

    A well sinks a list below the card it sits on, the way a column of cards sits below the
    tab around it, so a run of rows reads as one body rather than as content loose on the
    card. Alongside ``card()`` this is where the recessed depth theme is bound; the region
    sizes itself to its rows unless ``height`` reserves a footprint.
    """
    with dpg.child_window(
        tag=tag,
        parent=parent,
        width=-1,
        height=height,
        auto_resize_y=height == 0,
        border=False,
        no_scrollbar=True,
        show=show,
    ):
        yield tag

    ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_GROUND).bind_to_item(tag)
