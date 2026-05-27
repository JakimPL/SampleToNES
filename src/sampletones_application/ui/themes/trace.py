import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import COL_TEXT_TRACEBACK, TAG_THEME_TRACEBACK
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class TracebackTheme(Theme):
    tag: str = TAG_THEME_TRACEBACK
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvInputText): [
                ThemeColor(
                    key=dpg.mvThemeCol_Text,
                    color=COL_TEXT_TRACEBACK,
                ),
            ],
        }
    )
