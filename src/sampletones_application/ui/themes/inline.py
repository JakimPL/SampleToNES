from typing import cast

import dearpygui.dearpygui as dpg

from sampletones_shared.types.application import ColorRGBA


def create_selectable_text_theme(color: ColorRGBA) -> int:
    """Builds a theme colouring selectable text identically in both enabled states.

    DearPyGui resolves an item against the theme component that matches the
    item's enabled state. Carrying the colour in both components keeps the theme
    authoritative for the selectable in every state — including frames where its
    container is disabled — matching the loader's policy that a theme fully
    describes both item states.
    """
    with dpg.theme() as theme:
        for enabled_state in (True, False):
            with dpg.theme_component(dpg.mvSelectable, enabled_state=enabled_state):
                dpg.add_theme_color(
                    dpg.mvThemeCol_Text,
                    color,
                    category=dpg.mvThemeCat_Core,
                )

    return cast(int, theme)
