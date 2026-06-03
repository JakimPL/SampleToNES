import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_THEME_GLOBAL_INPUT_INVALID
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class InvalidInputTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_INPUT_INVALID
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        c = layout.colors
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvInputText): [
                    ThemeColor(key=dpg.mvThemeCol_FrameBg, color=c.backgrounds.input_invalid),
                ],
            }
        )
