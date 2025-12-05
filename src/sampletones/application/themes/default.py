from dataclasses import dataclass

import dearpygui.dearpygui as dpg

from ..constants import COL_TEXT_DEFAULT, COL_TEXT_DISABLED_DEFAULT, TAG_THEME_DEFAULT
from .theme import Theme


@dataclass(frozen=True)
class DefaultTheme(Theme):
    tag: str = TAG_THEME_DEFAULT

    def create(self) -> None:
        if dpg.does_item_exist(self.tag):
            return

        with dpg.theme(tag=self.tag):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, COL_TEXT_DEFAULT)
                dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, COL_TEXT_DISABLED_DEFAULT)
