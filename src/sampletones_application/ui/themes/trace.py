import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_GLOBAL_THEME_TRACEBACK
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class TracebackTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_TRACEBACK
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        colors = layout.colors
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvInputText): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=colors.text.traceback,
                    ),
                ],
            }
        )
