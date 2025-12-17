import dearpygui.dearpygui as dpg

from ..constants.general import (
    COL_BACKGROUND,
    COL_BACKGROUND_MENU,
    COL_BUTTON,
    COL_BUTTON_ACTIVE,
    COL_BUTTON_HOVERED,
    COL_TABLE_BACKGROUND_HEADER,
    COL_TABLE_BACKGROUND_ROW,
    COL_TABLE_BACKGROUND_ROW_ALTERNATIVE,
    COL_TABLE_BORDER,
    COL_TEXT_DEFAULT,
    COL_TEXT_DISABLED_DEFAULT,
    TAG_THEME_DEFAULT,
    VAL_BUTTON_FRAME_PADDING,
    VAL_BUTTON_FRAME_ROUNDING,
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
                ThemeColor(key=dpg.mvThemeCol_PopupBg, color=COL_BACKGROUND_MENU),
                ThemeColor(key=dpg.mvThemeCol_MenuBarBg, color=COL_BACKGROUND_MENU),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Button, color=COL_BUTTON),
                ThemeColor(key=dpg.mvThemeCol_ButtonHovered, color=COL_BUTTON_HOVERED),
                ThemeColor(key=dpg.mvThemeCol_ButtonActive, color=COL_BUTTON_ACTIVE),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_BUTTON_FRAME_ROUNDING),
                ThemeStyle(
                    key=dpg.mvStyleVar_FramePadding,
                    x=VAL_BUTTON_FRAME_PADDING[0],
                    y=VAL_BUTTON_FRAME_PADDING[1],
                ),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_BUTTON_FRAME_ROUNDING),
                ThemeStyle(
                    key=dpg.mvStyleVar_FramePadding,
                    x=VAL_BUTTON_FRAME_PADDING[0],
                    y=VAL_BUTTON_FRAME_PADDING[1],
                ),
            ],
            ThemeParameter(item_type=dpg.mvTable, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_TableHeaderBg, color=COL_TABLE_BACKGROUND_HEADER),
                ThemeColor(key=dpg.mvThemeCol_TableRowBg, color=COL_TABLE_BACKGROUND_ROW),
                ThemeColor(key=dpg.mvThemeCol_TableRowBgAlt, color=COL_TABLE_BACKGROUND_ROW_ALTERNATIVE),
                ThemeColor(key=dpg.mvThemeCol_TableBorderStrong, color=COL_TABLE_BORDER),
                ThemeColor(key=dpg.mvThemeCol_TableBorderLight, color=COL_TABLE_BORDER),
            ],
        }
    )
