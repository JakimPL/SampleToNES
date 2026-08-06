from __future__ import annotations

from typing import List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.ui.themes.items import ThemeDictionary, ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
    ThemeValue,
)
from sampletones_application.utils.palette.color import PaletteColor
from sampletones_shared.types.application import ColorRGBA, Sender

ThemeColorItems = List[Tuple[Sender, PaletteColor]]


class Theme:
    def __init__(self, *, tag: str, items: ThemeItems) -> None:
        self.tag = tag
        self._items = items
        self._dictionary: ThemeDictionary = self._index(items)
        self._color_items: ThemeColorItems = []

    @staticmethod
    def _index(items: ThemeItems) -> ThemeDictionary:
        """Index every entry by its merge identity so a value reads back before the DPG theme is created.

        The lookup derives from the resolved definition alone, so ``get_color``/``get_style`` answer
        as soon as the theme is registered, ahead of the first bind that builds the DPG items.
        """
        dictionary: ThemeDictionary = {}
        for parameter, values in items.items.items():
            for item in values:
                dictionary[
                    parameter,
                    item.key,
                    item.category,
                    isinstance(item, ThemeStyle),
                ] = item

        return dictionary

    def create(self) -> None:
        """Builds the DearPyGui theme once, keeping hold of the colour items it fills.

        DearPyGui copies each colour into the item it creates, so the theme records the
        item alongside the :class:`PaletteColor` it was filled from and :meth:`restyle`
        writes the current value back into it.
        """
        if dpg.does_item_exist(self.tag):
            return

        with dpg.theme(tag=self.tag):
            for parameter, values in self._items.items.items():
                with dpg.theme_component(
                    parameter.item_type,
                    enabled_state=parameter.enabled_state,
                ):
                    for item in values:
                        if isinstance(item, ThemeColor):
                            self._add_color(item)
                        elif isinstance(item, ThemeStyle):
                            dpg.add_theme_style(
                                item.key,
                                item.x,
                                item.y,
                                category=item.category,
                            )

    def _add_color(self, item: ThemeColor) -> None:
        color_item = dpg.add_theme_color(
            item.key,
            item.color.rgba,
            category=item.category,
        )
        self._color_items.append((color_item, item.color))

    def restyle(self) -> None:
        """Writes the current value of every colour this theme carries back into DearPyGui.

        Setting a live theme colour item repaints each item bound to the theme on the next
        frame and leaves the bindings themselves in place, so a palette swap reaches every
        themed widget through the theme it already has.
        """
        for color_item, color in self._color_items:
            dpg.set_value(color_item, color.rgba)

    def bind_to_item(self, item: int | str) -> None:
        self.create()
        dpg.bind_item_theme(item, self.tag)

    def bind(self) -> None:
        self.create()
        dpg.bind_theme(self.tag)

    def get(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
        category: int = dpg.mvThemeCat_Core,
        is_style: bool,
    ) -> Optional[ThemeValue]:
        parameter = ThemeParameter(
            item_type=item_type,
            enabled_state=enabled_state,
        )
        return self._dictionary.get((parameter, key, category, is_style))

    def get_color(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
        category: int = dpg.mvThemeCat_Core,
    ) -> Optional[ColorRGBA]:
        """The value a theme colour carries under the active palette."""
        theme_item = self.get(
            item_type,
            key,
            enabled_state=enabled_state,
            category=category,
            is_style=False,
        )
        if isinstance(theme_item, ThemeColor):
            return theme_item.color.rgba

        return None

    def get_style(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
        category: int = dpg.mvThemeCat_Core,
    ) -> Optional[Tuple[float, float]]:
        theme_item = self.get(
            item_type,
            key,
            enabled_state=enabled_state,
            category=category,
            is_style=True,
        )
        if isinstance(theme_item, ThemeStyle):
            return theme_item.x, theme_item.y

        return None

    def get_category(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
    ) -> Optional[int]:
        for category in (dpg.mvThemeCat_Core, dpg.mvThemeCat_Plots):
            for is_style in (False, True):
                theme_item = self.get(
                    item_type,
                    key,
                    enabled_state=enabled_state,
                    category=category,
                    is_style=is_style,
                )
                if theme_item is not None:
                    return theme_item.category

        return None
