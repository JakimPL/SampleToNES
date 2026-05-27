import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    TAG_THEME_TABLE,
    VAL_TABLE_CELL_PADDING,
    VAL_TABLE_FRAME_ROUNDING,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class TableTheme(Theme):
    tag: str = TAG_THEME_TABLE
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_TABLE_FRAME_ROUNDING),
            ],
        }
    )
