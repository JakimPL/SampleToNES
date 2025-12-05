from typing import Any, Callable, Dict

import dearpygui.dearpygui as dpg


class Theme:
    REGISTRY: Dict[str, "Theme"] = {}
    tag: str

    def __init__(self) -> None:
        Theme.REGISTRY[self.tag] = self

    def __new__(cls) -> "Theme":
        if cls.tag in cls.REGISTRY:
            return cls.REGISTRY[cls.tag]

        instance = super(Theme, cls).__new__(cls)
        return instance

    def create(self, override: bool = True) -> None:
        raise NotImplementedError("Subclasses must implement _create method")

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
