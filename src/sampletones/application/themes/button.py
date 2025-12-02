from dataclasses import dataclass

import dearpygui.dearpygui as dpg

from ..constants import (
    COL_BUTTON,
    COL_BUTTON_ACTIVE,
    COL_BUTTON_HOVERED,
    TAG_THEME_BUTTON,
    VAL_BUTTON_FRAME_PADDING,
    VAL_BUTTON_FRAME_ROUNDING,
)
from .theme import Theme


@dataclass(frozen=True)
class ButtonTheme(Theme):
    tag: str = TAG_THEME_BUTTON

    def create(self) -> None:
        if dpg.does_item_exist(self.tag):
            return

        with dpg.theme(tag=self.tag):
            with dpg.theme_component(enabled_state=True):
                dpg.add_theme_color(dpg.mvThemeCol_Button, COL_BUTTON, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COL_BUTTON_HOVERED, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, COL_BUTTON_ACTIVE, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(
                    dpg.mvStyleVar_FrameRounding, VAL_BUTTON_FRAME_ROUNDING, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_FramePadding, *VAL_BUTTON_FRAME_PADDING, category=dpg.mvThemeCat_Core
                )
            with dpg.theme_component(enabled_state=False):
                dpg.add_theme_style(
                    dpg.mvStyleVar_FrameRounding, VAL_BUTTON_FRAME_ROUNDING, category=dpg.mvThemeCat_Core
                )
                dpg.add_theme_style(
                    dpg.mvStyleVar_FramePadding, *VAL_BUTTON_FRAME_PADDING, category=dpg.mvThemeCat_Core
                )
