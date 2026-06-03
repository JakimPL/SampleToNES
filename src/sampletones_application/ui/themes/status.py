import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    COL_BACKGROUND_MENU,
    COL_TEXT_DEFAULT,
    TAG_THEME_GLOBAL_STATUS,
    VAL_STATUS_FRAME_PADDING,
    VAL_STATUS_FRAME_ROUNDING,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class StatusBarTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_STATUS
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvAll): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DEFAULT),
                ThemeColor(key=dpg.mvThemeCol_TextDisabled, color=COL_TEXT_DEFAULT, category=dpg.mvThemeCat_Core),
                ThemeStyle(key=dpg.mvStyleVar_ButtonTextAlign, x=0.0, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_Button, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
                ThemeColor(
                    key=dpg.mvThemeCol_ButtonHovered,
                    color=COL_BACKGROUND_MENU,
                    category=dpg.mvThemeCat_Core,
                ),
                ThemeColor(key=dpg.mvThemeCol_ButtonActive, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_FrameBg, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_WindowBg, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DEFAULT, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_TextDisabled, color=COL_TEXT_DEFAULT, category=dpg.mvThemeCat_Core),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DEFAULT, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_TextDisabled, color=COL_TEXT_DEFAULT, category=dpg.mvThemeCat_Core),
                ThemeStyle(key=dpg.mvStyleVar_ButtonTextAlign, x=0.0, category=dpg.mvThemeCat_Core),
                ThemeStyle(key=dpg.mvStyleVar_FrameRounding, x=VAL_STATUS_FRAME_ROUNDING),
                ThemeStyle(
                    key=dpg.mvStyleVar_FramePadding,
                    x=VAL_STATUS_FRAME_PADDING[0],
                    y=VAL_STATUS_FRAME_PADDING[1],
                ),
            ],
        }
    )
