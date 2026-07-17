from contextlib import contextmanager
from typing import Iterator

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_THEME_PANEL_SURFACE
from sampletones_application.ui.themes.registry import ThemeRegistry


@contextmanager
def card(
    parent: str,
    tag: str,
    *,
    theme: str = TAG_GLOBAL_THEME_PANEL_SURFACE,
    width: int = -1,
    height: int = 0,
    auto_resize_y: bool = True,
    no_scrollbar: bool = False,
    show: bool = True,
) -> Iterator[str]:
    """Open a bordered, raised card inside ``parent`` and bind its depth theme.

    A card is the raised surface one module's content sits on: the tab coordinator
    lays cards out on the recessed columns ``TabColumns`` builds, and this context
    manager is the sole binder of the raised depth theme. Content added inside the
    ``with`` block lands in the card; ``tag`` is yielded so the caller can parent
    widgets built outside the block. The depth theme is a parameter so a toolbar
    card can sit on a surface distinct from a content card.
    """
    with dpg.child_window(
        tag=tag,
        parent=parent,
        width=width,
        height=height,
        auto_resize_y=auto_resize_y,
        border=True,
        no_scrollbar=no_scrollbar,
        show=show,
    ):
        yield tag

    ThemeRegistry.get(theme).bind_to_item(tag)
