import dearpygui.dearpygui as dpg

from ..constants import (
    COL_BACKGROUND,
    COL_BUTTON,
    COL_BUTTON_ACTIVE,
    COL_BUTTON_HOVERED,
    COL_TABLE_BORDER,
    COL_TABLE_HEADER_BACKGROUND,
    COL_TABLE_ROW_ALTERNATIVE_BACKGROUND,
    COL_TABLE_ROW_BACKGROUND,
    COL_TEXT_DEFAULT,
    COL_TEXT_DISABLED_DEFAULT,
    TAG_THEME_DEFAULT,
    VAL_BUTTON_FRAME_PADDING,
    VAL_BUTTON_FRAME_ROUNDING,
    VAL_TABLE_CELL_PADDING,
    VAL_TABLE_FRAME_ROUNDING,
)
from .items import ThemeColor, ThemeItems, ThemeParameter, ThemeStyle
from .theme import Theme


class DefaultTheme(Theme):
    tag: str = TAG_THEME_DEFAULT
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvAll, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DEFAULT),
                ThemeColor(key=dpg.mvThemeCol_TextDisabled, color=COL_TEXT_DISABLED_DEFAULT),
                ThemeColor(key=dpg.mvThemeCol_WindowBg, color=COL_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_ChildBg, color=COL_BACKGROUND),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Button, color=COL_BUTTON),
                ThemeColor(key=dpg.mvThemeCol_ButtonHovered, color=COL_BUTTON_HOVERED),
                ThemeColor(key=dpg.mvThemeCol_ButtonActive, color=COL_BUTTON_ACTIVE),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_BUTTON_FRAME_ROUNDING),
                ThemeStyle(
                    key=dpg.mvStyleVar_FramePadding, x=VAL_BUTTON_FRAME_PADDING[0], y=VAL_BUTTON_FRAME_PADDING[1]
                ),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_BUTTON_FRAME_ROUNDING),
                ThemeStyle(
                    key=dpg.mvStyleVar_FramePadding, x=VAL_BUTTON_FRAME_PADDING[0], y=VAL_BUTTON_FRAME_PADDING[1]
                ),
            ],
            ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_TableHeaderBg, color=COL_TABLE_HEADER_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableRowBg, color=COL_TABLE_ROW_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableRowBgAlt, color=COL_TABLE_ROW_ALTERNATIVE_BACKGROUND),
                ThemeColor(key=dpg.mvThemeCol_TableBorderStrong, color=COL_TABLE_BORDER),
                ThemeColor(key=dpg.mvThemeCol_TableBorderLight, color=COL_TABLE_BORDER),
                ThemeStyle(key=dpg.mvStyleVar_CellPadding, x=VAL_TABLE_CELL_PADDING[0], y=VAL_TABLE_CELL_PADDING[1]),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_TABLE_FRAME_ROUNDING),
            ],
        }
    )
