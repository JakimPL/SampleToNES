import dearpygui.dearpygui as dpg

from ..constants.general import COL_TEXT_TRACEBACK, TAG_THEME_TRACEBACK
from .items import ThemeColor, ThemeItems, ThemeParameter
from .theme import Theme


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
