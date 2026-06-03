import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    COL_TEXT_FAVORITE,
    COL_TEXT_FAVORITE_CHILD,
    TAG_THEME_GLOBAL_FAVORITE,
    TAG_THEME_GLOBAL_FAVORITE_CHILD,
)
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class FavoriteNodeTheme(Theme):
    tag: str = TAG_THEME_GLOBAL_FAVORITE
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
    tag: str = TAG_THEME_GLOBAL_FAVORITE_CHILD
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
