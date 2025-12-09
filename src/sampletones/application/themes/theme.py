from typing import Any, Callable, Dict, ItemsView, KeysView, List, Union, ValuesView

import dearpygui.dearpygui as dpg

from .items import ThemeColor, ThemeItems, ThemeParameter, ThemeStyle


class Theme:
    REGISTRY: Dict[str, "Theme"] = {}

    tag: str
    _theme: ThemeItems

    def __init__(self) -> None:
        Theme.REGISTRY[self.tag] = self

    def __new__(cls) -> "Theme":
        if cls.tag in cls.REGISTRY:
            return cls.REGISTRY[cls.tag]

        instance = super(Theme, cls).__new__(cls)
        return instance

    @classmethod
    def keys(cls) -> KeysView[ThemeParameter]:
        return cls._theme.items.keys()

    @classmethod
    def items(cls) -> ItemsView[ThemeParameter, List[Union[ThemeColor, ThemeStyle]]]:
        return cls._theme.items.items()

    @classmethod
    def values(cls) -> ValuesView[List[Union[ThemeColor, ThemeStyle]]]:
        return cls._theme.items.values()

    def create(self, override: bool = False) -> None:
        if not override and dpg.does_item_exist(self.tag):
            return

        if override and dpg.does_item_exist(self.tag):
            dpg.delete_item(self.tag)

        with dpg.theme(tag=self.tag):
            for parameter, items in self.items():
                with dpg.theme_component(parameter.item_type, enabled_state=parameter.enabled_state):
                    for item in items:
                        if isinstance(item, ThemeColor):
                            dpg.add_theme_color(item.key, item.color, category=item.category)
                        elif isinstance(item, ThemeStyle):
                            dpg.add_theme_style(item.key, item.x, item.y, category=item.category)

    @staticmethod
    def create_before_bind(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: "Theme", *args: Any, **kwargs: Any) -> Any:
            self.create()
            return func(self, *args, **kwargs)

        return wrapper

    @create_before_bind
    def bind_to_item(self, item: str) -> None:
        dpg.bind_item_theme(item, self.tag)

    @create_before_bind
    def bind(self) -> None:
        dpg.bind_theme(self.tag)
