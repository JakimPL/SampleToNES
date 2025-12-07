import dearpygui.dearpygui as dpg

from ..constants import (
    COL_BACKGROUND_LIGHT,
    COL_BUTTON_LIGHT,
    COL_TEXT_DISABLED_DEFAULT,
    COL_TEXT_WHITE,
    TAG_THEME_CONVERTER,
)
from .items import ThemeColor, ThemeItems, ThemeParameter
from .theme import Theme


class ConverterTheme(Theme):
    tag: str = TAG_THEME_CONVERTER
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvAll, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_WHITE),
                ThemeColor(key=dpg.mvThemeCol_TextDisabled, color=COL_TEXT_DISABLED_DEFAULT),
                ThemeColor(key=dpg.mvThemeCol_WindowBg, color=COL_BACKGROUND_LIGHT),
                ThemeColor(key=dpg.mvThemeCol_ChildBg, color=COL_BACKGROUND_LIGHT),
            ],
            ThemeParameter(item_type=dpg.mvButton, enabled_state=True): [
                ThemeColor(key=dpg.mvThemeCol_Button, color=COL_BUTTON_LIGHT),
            ],
        }
    )
