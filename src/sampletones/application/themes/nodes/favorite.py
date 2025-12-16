import dearpygui.dearpygui as dpg

from ...constants.general import (
    COL_TEXT_FAVORITE,
    COL_TEXT_FAVORITE_CHILD,
    TAG_THEME_FAVORITE,
    TAG_THEME_FAVORITE_CHILD,
)
from ..items import ThemeItems
from ..style import ThemeColor, ThemeParameter
from ..theme import Theme


class FavoriteNodeTheme(Theme):
    tag: str = TAG_THEME_FAVORITE
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTreeNode): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FAVORITE),
            ],
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FAVORITE),
            ],
        }
    )


class FavoriteChildNodeTheme(Theme):
    tag: str = TAG_THEME_FAVORITE_CHILD
    _theme: ThemeItems = ThemeItems(
        items={
            ThemeParameter(item_type=dpg.mvTreeNode): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FAVORITE_CHILD),
            ],
            ThemeParameter(item_type=dpg.mvSelectable): [
                ThemeColor(key=dpg.mvThemeCol_Text, color=COL_TEXT_FAVORITE_CHILD),
            ],
        }
    )
