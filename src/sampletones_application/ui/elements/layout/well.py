import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_GROUP,
    TAG_GLOBAL_THEME_PANEL_GROUND,
)
from sampletones_application.ui.themes.registry import ThemeRegistry


def well(
    parent: str,
    tag: str,
    *,
    padding: int,
    margin: int,
    height: int = 0,
    show: bool = True,
) -> str:
    """Sink a recessed region into a card and bind its depth theme.

    A well sinks a list below the card it sits on, the way a column of cards sits below the
    tab around it, so a run of rows reads as one body rather than as content loose on the
    card. Alongside ``card()`` this is where the recessed depth theme is bound; the region
    sizes itself to its rows unless ``height`` reserves a footprint.

    Returns the inset body group content is added to, which keeps ``padding`` clear at the
    sides. ``margin`` opens the gap above the first row and below the last, which the row
    spacing between the content and the spacers adds to.
    """
    body_tag = compose_tag(tag, SUF_GROUP)
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
        dpg.add_spacer(height=margin)
        dpg.add_group(tag=body_tag, indent=padding, width=-padding)
        dpg.add_spacer(height=margin)

    ThemeRegistry.get(TAG_GLOBAL_THEME_PANEL_GROUND).bind_to_item(tag)
    return body_tag
