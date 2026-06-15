import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_CONVERTER
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class ConverterTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_CONVERTER
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        color = layout.colors
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvAll, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=color.text.white,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_TextDisabled,
                        color=color.text.disabled,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_WindowBg,
                        color=color.backgrounds.light,
                    ),
                    ThemeColor(
                        key=dpg.mvThemeCol_ChildBg,
                        color=color.backgrounds.light,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Button,
                        color=color.buttons.light,
                    ),
                ],
            }
        )
