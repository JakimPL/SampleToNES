import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_MENU_FPS
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class FPSTimerTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_MENU_FPS
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        colors = layout.colors
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                    ThemeStyle(
                        key=dpg.mvStyleVar_ButtonTextAlign,
                        x=1.0,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=colors.text.disabled,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_Button,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ButtonHovered,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ButtonActive,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_MenuBarBg,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                ],
            }
        )
