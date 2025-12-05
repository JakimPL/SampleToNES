from dataclasses import dataclass

import dearpygui.dearpygui as dpg

from ..constants import (
    COL_TABLE_BORDER,
    COL_TABLE_HEADER_BACKGROUND,
    COL_TABLE_ROW_ALTERNATIVE_BACKGROUND,
    COL_TABLE_ROW_BACKGROUND,
    TAG_THEME_TABLE,
    VAL_TABLE_CELL_PADDING,
    VAL_TABLE_FRAME_ROUNDING,
)
from .theme import Theme


@dataclass(frozen=True)
class TableTheme(Theme):
    tag: str = TAG_THEME_TABLE

    def create(self, override: bool = False) -> None:
        if not override and dpg.does_item_exist(self.tag):
            return

        if override and dpg.does_item_exist(self.tag):
            dpg.delete_item(self.tag)

        with dpg.theme(tag=self.tag):
            with dpg.theme_component(dpg.mvTable):
                dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, COL_TABLE_HEADER_BACKGROUND)
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, COL_TABLE_ROW_BACKGROUND)
                dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, COL_TABLE_ROW_ALTERNATIVE_BACKGROUND)
                dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, COL_TABLE_BORDER)
                dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, COL_TABLE_BORDER)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding, *VAL_TABLE_CELL_PADDING)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, VAL_TABLE_FRAME_ROUNDING)
