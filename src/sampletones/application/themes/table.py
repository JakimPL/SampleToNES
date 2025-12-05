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
from .items import ThemeColor, ThemeItems, ThemeParameter, ThemeStyle
from .theme import Theme


class TableTheme(Theme):
    tag: str = TAG_THEME_TABLE
    _items: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_TableHeaderBg, color=COL_TABLE_HEADER_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableRowBg, color=COL_TABLE_ROW_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableRowBgAlt, color=COL_TABLE_ROW_ALTERNATIVE_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableBorderStrong, color=COL_TABLE_BORDER),
                ThemeColor(key=dpg.mvThemeCol_TableBorderLight, color=COL_TABLE_BORDER),
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_TABLE_FRAME_ROUNDING),
            ]
        }
    )
