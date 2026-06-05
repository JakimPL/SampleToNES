import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import (
    TAG_GLOBAL_THEME_FAVORITE,
    TAG_GLOBAL_THEME_FAVORITE_CHILD,
)
from sampletones_application.layout.general import GeneralLayout
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter
from sampletones_application.ui.themes.theme import Theme


class FavoriteNodeTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_FAVORITE
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.favorites.default,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvSelectable): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.favorites.default,
                    ),
                ],
            }
        )


class FavoriteChildNodeTheme(Theme):
    tag: str = TAG_GLOBAL_THEME_FAVORITE_CHILD
    _theme: ThemeItems = ThemeItems()

    @classmethod
    def setup(cls, layout: GeneralLayout) -> None:
        cls._theme = ThemeItems(
            items={
                ThemeParameter(item_type=dpg.mvTreeNode): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.favorites.child,
                    ),
                ],
                ThemeParameter(item_type=dpg.mvSelectable): [
                    ThemeColor(
                        key=dpg.mvThemeCol_Text,
                        color=layout.colors.favorites.child,
                    ),
                ],
            }
        )
