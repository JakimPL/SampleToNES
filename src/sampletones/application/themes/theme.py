from dataclasses import dataclass
from typing import Any, Callable

import dearpygui.dearpygui as dpg


@dataclass(frozen=True)
class Theme:
    tag: str

    def create(self) -> None:
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
