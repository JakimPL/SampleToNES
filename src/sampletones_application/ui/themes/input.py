import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import COL_BACKGROUND_INPUT_INVALID, TAG_THEME_INPUT_INVALID
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class InvalidInputTheme(Theme):
    tag: str = TAG_THEME_INPUT_INVALID
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvInputText): [
                ThemeColor(key=dpg.mvThemeCol_FrameBg, color=COL_BACKGROUND_INPUT_INVALID),
            ],
        }
    )
