import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_STATUS
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
)
from sampletones_application.ui.themes.theme import Theme


class StatusBarTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_STATUS
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        colors = layout.colors
        status_bar = layout.status_bar
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvAll): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=colors.text.default,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TextDisabled,
                        color=colors.text.default,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_ButtonTextAlign,
                        x=0.0,
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
                        key=dpg.mvThemeCol_FrameBg,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_WindowBg,
                        color=colors.backgrounds.menu,
                        category=dpg.mvThemeCat_Core,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=colors.text.default,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TextDisabled,
                        color=colors.text.default,
                        category=dpg.mvThemeCat_Core,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvButton, enabled_state=False): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=colors.text.default,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TextDisabled,
                        color=colors.text.default,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_ButtonTextAlign,
                        x=0.0,
                        category=dpg.mvThemeCat_Core,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FrameRounding,
                        x=status_bar.frame_rounding,
                    ),
                    ThemeStyle(
                        key=dpg.mvStyleVar_FramePadding,
                        x=status_bar.frame_padding[0],
                        y=status_bar.frame_padding[1],
                    ),
                ],
            }
        )
