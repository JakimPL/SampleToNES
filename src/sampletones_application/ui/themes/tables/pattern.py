import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import COL_BLANK, VAL_TABLE_CELL_PADDING
from sampletones_application.constants.sequencer import COL_PATTERN_HIGHLIGHT, TAG_THEME_TABLE_PATTERN
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class PatternTableTheme(Theme):
    tag: str = TAG_THEME_TABLE_PATTERN
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable): [
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeColor(key=dpg.mvThemeCol_HeaderHovered, color=COL_PATTERN_HIGHLIGHT),
                ThemeColor(key=dpg.mvThemeCol_HeaderActive, color=COL_BLANK),
            ],
        }
    )
