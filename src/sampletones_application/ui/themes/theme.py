from __future__ import annotations

from typing import Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.ui.themes.items import ThemeDictionary, ThemeItems
from sampletones_application.ui.themes.style import (
    ThemeColor,
    ThemeParameter,
    ThemeStyle,
    ThemeValue,
)
from sampletones_shared.types.application import Color


class Theme:
    def __init__(self, *, tag: str, items: ThemeItems) -> None:
        self.tag = tag
        self._items = items
        self._dictionary: ThemeDictionary = {}

    def create(self, *, override: bool = False) -> None:
        if not override and dpg.does_item_exist(self.tag):
            return

        if override and dpg.does_item_exist(self.tag):
            dpg.delete_item(self.tag)

        dictionary: ThemeDictionary = {}
        with dpg.theme(tag=self.tag):
            for parameter, values in self._items.items.items():
                with dpg.theme_component(
                    parameter.item_type,
                    enabled_state=parameter.enabled_state,
                ):
                    for item in values:
                        dictionary[parameter, item.key] = item
                        if isinstance(item, ThemeColor):
                            dpg.add_theme_color(
                                item.key,
                                item.color,
                                category=item.category,
                            )
                        elif isinstance(item, ThemeStyle):
                            dpg.add_theme_style(
                                item.key,
                                item.x,
                                item.y,
                                category=item.category,
                            )

        self._dictionary = dictionary

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
    ) -> Optional[ThemeValue]:
        parameter = ThemeParameter(
            item_type=item_type,
            enabled_state=enabled_state,
        )
        return self._dictionary.get((parameter, key))

    def get_color(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
    ) -> Optional[Color]:
        theme_item = self.get(item_type, key, enabled_state=enabled_state)
        if isinstance(theme_item, ThemeColor):
            return theme_item.color
        return None

    def get_style(
        self,
        item_type: int,
        key: int,
        *,
        enabled_state: bool = True,
    ) -> Optional[Tuple[float, float]]:
        theme_item = self.get(item_type, key, enabled_state=enabled_state)
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
        theme_item = self.get(item_type, key, enabled_state=enabled_state)
        if theme_item is not None:
            return theme_item.category
        return None
