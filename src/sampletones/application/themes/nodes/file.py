import dearpygui.dearpygui as dpg

from ...constants.general import (
    COL_TEXT_DISABLED_DEFAULT,
    COL_TEXT_FILE_LIBRARY,
    COL_TEXT_FILE_RECONSTRUCTION,
    COL_TEXT_FILE_WAVE,
    TAG_THEME_FILE_LIBRARY,
    TAG_THEME_FILE_NO_CONTENT,
    TAG_THEME_FILE_RECONSTRUCTION,
    TAG_THEME_FILE_WAVE,
)
from ..items import ThemeColor, ThemeItems, ThemeParameter
from ..theme import Theme


class NoContentFileNodeTheme(Theme):
    tag: str = TAG_THEME_FILE_NO_CONTENT
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTreeNode): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DISABLED_DEFAULT),
            ],
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_DISABLED_DEFAULT),
            ],
        }
    )


class ReconstructionFileNodeTheme(Theme):
    tag: str = TAG_THEME_FILE_RECONSTRUCTION
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FILE_RECONSTRUCTION),
            ],
        }
    )


class LibraryFileNodeTheme(Theme):
    tag: str = TAG_THEME_FILE_LIBRARY
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FILE_LIBRARY),
            ],
        }
    )


class WaveFileNodeTheme(Theme):
    tag: str = TAG_THEME_FILE_WAVE
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FILE_WAVE),
            ],
        }
    )
