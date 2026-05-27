from __future__ import annotations

from typing import Any, Dict, ItemsView, KeysView, Optional, Tuple, ValuesView

import dearpygui.dearpygui as dpg

from sampletones_application.ui.themes.items import ThemeDictionary, ThemeItems, ThemeValues
from sampletones_application.ui.themes.style import ThemeColor, ThemeParameter, ThemeStyle, ThemeValue
from sampletones_shared.types.application import Color
from sampletones_shared.types.callback import Callback


class Theme:
    _REGISTRY: Dict[str, Theme] = {}

    tag: str
    _theme: ThemeItems
    _dictionary: ThemeDictionary

    def __init__(self) -> None:
        Theme._REGISTRY[self.tag] = self

    def __new__(cls) -> Theme:
        if cls.tag in cls._REGISTRY:
            return cls._REGISTRY[cls.tag]

        instance = super(Theme, cls).__new__(cls)
        return instance

    def __getitem__(self, key: Tuple[ThemeParameter, int]) -> ThemeValue:
        return self._dictionary[key]

    @classmethod
    def get(
        cls,
        item_type: int,
        key: int,
        enabled_state: bool = True,
    ) -> Optional[ThemeValue]:
        parameter = ThemeParameter(item_type=item_type, enabled_state=enabled_state)
        if (parameter, key) not in cls._dictionary:
            return None

        return cls._dictionary[parameter, key]

    @classmethod
    def get_color(
        cls,
        item_type: int,
        key: int,
        enabled_state: bool = True,
    ) -> Optional[Color]:
        theme_item = cls.get(item_type, key, enabled_state)
        if isinstance(theme_item, ThemeColor):
            return theme_item.color

        return None

    @classmethod
    def get_style(
        cls,
        item_type: int,
        key: int,
        enabled_state: bool = True,
    ) -> Optional[Tuple[float, float]]:
        theme_item = cls.get(item_type, key, enabled_state)
        if isinstance(theme_item, ThemeStyle):
            return theme_item.x, theme_item.y

        return None

    @classmethod
    def get_category(
        cls,
        item_type: int,
        key: int,
        enabled_state: bool = True,
    ) -> Optional[int]:
        theme_item = cls.get(item_type, key, enabled_state)
        if theme_item is not None:
            return theme_item.category

        return None

    @classmethod
    def keys(cls) -> KeysView[ThemeParameter]:
        return cls._theme.items.keys()

    @classmethod
    def items(cls) -> ItemsView[ThemeParameter, ThemeValues]:
        return cls._theme.items.items()

    @classmethod
    def values(cls) -> ValuesView[ThemeValues]:
        return cls._theme.items.values()

    @classmethod
    def create(cls, override: bool = False) -> None:
        if not override and dpg.does_item_exist(cls.tag):
            return

        if override and dpg.does_item_exist(cls.tag):
            dpg.delete_item(cls.tag)

        dictionary: ThemeDictionary = {}
        with dpg.theme(tag=cls.tag):
            for parameter, items in cls.items():
                with dpg.theme_component(parameter.item_type, enabled_state=parameter.enabled_state):
                    for item in items:
                        dictionary[parameter, item.key] = item
                        if isinstance(item, ThemeColor):
                            dpg.add_theme_color(item.key, item.color, category=item.category)
                        elif isinstance(item, ThemeStyle):
                            dpg.add_theme_style(item.key, item.x, item.y, category=item.category)

        cls._dictionary = dictionary

    @staticmethod
    def create_before_bind(func: Callback) -> Callback:
        def wrapper(self: Theme, *args: Any, **kwargs: Any) -> Any:
            self.create()
            return func(self, *args, **kwargs)

        return wrapper

    @create_before_bind
    def bind_to_item(self, item: str) -> None:
        dpg.bind_item_theme(item, self.tag)

    @create_before_bind
    def bind(self) -> None:
        dpg.bind_theme(self.tag)
