from typing import Dict, cast

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.utils.palette.colors.base import BaseColor


def create_selectable_text_theme(color: BaseColor) -> int:
    """Builds a theme colouring selectable text, leaving its other colours to the global theme."""
    return _create_selectable_theme({dpg.mvThemeCol_Text: color})


def create_header_selectable_theme(
    text_color: BaseColor,
    hovered_color: BaseColor,
    active_color: BaseColor,
) -> int:
    """Builds a theme for a selectable that carries a table column's label.

    A selectable takes the ``Header`` colours under the pointer, so naming those alongside the
    text colour gives a header label the pointer feedback a table header has, in place of the
    selection shade a cell takes.
    """
    return _create_selectable_theme(
        {
            dpg.mvThemeCol_Text: text_color,
            dpg.mvThemeCol_HeaderHovered: hovered_color,
            dpg.mvThemeCol_HeaderActive: active_color,
        },
    )


def _create_selectable_theme(colors: Dict[int, BaseColor]) -> int:
    """Builds a theme carrying ``colors`` for a selectable in both enabled states.

    DearPyGui resolves an item against the theme component that matches the
    item's enabled state. Carrying the colour in both components keeps the theme
    authoritative for the selectable in every state — including frames where its
    container is disabled — matching the loader's policy that a theme fully
    describes both item states.
    """
    with dpg.theme() as theme:
        for enabled_state in (True, False):
            with dpg.theme_component(
                dpg.mvSelectable,
                enabled_state=enabled_state,
            ):
                for key, color in colors.items():
                    dpg_add_palette_theme_color(
                        key,
                        color,
                        category=dpg.mvThemeCat_Core,
                    )

    return cast(int, theme)


def create_vertical_spacer_theme() -> int:
    """Builds a theme that collapses item spacing to zero for a vertically stacked group.

    DearPyGui inserts ItemSpacing before each item in a stack. Bound to a section header's
    marker group, this theme zeroes that spacing so a single leading spacer becomes the exact,
    sole control over the marker glyph's drop: the spacer's height is how far the marker sits
    below the group's top. The group stacks only vertically, so zeroing both axes leaves its
    layout unchanged apart from that gap.
    """
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_style(
                dpg.mvStyleVar_ItemSpacing,
                0,
                0,
                category=dpg.mvThemeCat_Core,
            )

    return cast(int, theme)
