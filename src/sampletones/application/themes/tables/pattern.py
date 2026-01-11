import dearpygui.dearpygui as dpg

from ...constants.general import COL_BLANK, VAL_TABLE_CELL_PADDING
from ...constants.sequencer import COL_PATTERN_HIGHLIGHT, TAG_THEME_TABLE_PATTERN
from ..items import ThemeItems
from ..style import ThemeColor, ThemeParameter, ThemeStyle
from ..theme import Theme


class PatternTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_PATTERN
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable): [
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeStyle(key=dpg.mvStyleVar_SelectableTextAlign, x=0.5, y=0.5),
                ThemeColor(key=dpg.mvThemeCol_HeaderHovered, color=COL_PATTERN_HIGHLIGHT),
                ThemeColor(key=dpg.mvThemeCol_HeaderActive, color=COL_BLANK),
                ThemeStyle(key=dpg.mvStyleVar_TableAngledHeadersTextAlign, x=0.5, y=0.5),
                ThemeStyle(key=dpg.mvStyleVar_SeparatorTextAlign, x=0.5, y=0.5),
            ],
        }
    )
