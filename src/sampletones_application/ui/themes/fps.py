import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    COL_BACKGROUND_MENU,
    COL_TEXT_DISABLED_DEFAULT,
    TAG_THEME_MENU_FPS,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter, ThemeStyle
from sampletones_application.ui.themes.theme import Theme


class FPSTimerTheme(Theme):
    tag: str = TAG_THEME_MENU_FPS
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                ThemeStyle(key=dpg.mvStyleVar_ButtonTextAlign, x=1.0, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DISABLED_DEFAULT, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_Button, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
                ThemeColor(
                    key=dpg.mvThemeCol_ButtonHovered,
                    color=COL_BACKGROUND_MENU,
                    category=dpg.mvThemeCat_Core,
                ),
                ThemeColor(key=dpg.mvThemeCol_ButtonActive, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
                ThemeColor(key=dpg.mvThemeCol_MenuBarBg, color=COL_BACKGROUND_MENU, category=dpg.mvThemeCat_Core),
            ],
        }
    )
