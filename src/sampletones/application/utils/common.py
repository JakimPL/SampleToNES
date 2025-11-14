import functools
from typing import Any, Callable, Optional

import dearpygui.dearpygui as dpg

from ..elements.button import GUIButton


def dpg_wrapper(button_function: Optional[Callable] = None) -> Callable:
    def decorator(function: Callable) -> Callable:
        @functools.wraps(function)
        def wrapper(tag: str, *args, **kwargs) -> None:
            if button_function is not None and tag in GUIButton.REGISTRY:
                button_function(GUIButton.REGISTRY[tag], *args, **kwargs)
            elif dpg.does_item_exist(tag):
                return function(tag, *args, **kwargs)

        return wrapper

    return decorator


@dpg_wrapper(button_function=GUIButton.delete_item)
def dpg_delete_item(tag: str, **kwargs) -> None:
    dpg.delete_item(tag, **kwargs)


def dpg_delete_children(tag: str) -> None:
    dpg_delete_item(tag, children_only=True)


def dpg_bind_item_theme(tag: str, theme_tag: str) -> None:
    if dpg.does_item_exist(tag) and dpg.does_item_exist(theme_tag):
        dpg.bind_item_theme(tag, theme_tag)


@dpg_wrapper(button_function=GUIButton.configure_item)
def dpg_configure_item(tag: str, **kwargs) -> None:
    return dpg.configure_item(tag, **kwargs)


@dpg_wrapper(button_function=GUIButton.set_item_callback)
def dpg_set_item_callback(tag: str, callback: Callable) -> None:
    return dpg.set_item_callback(tag, callback=callback)


@dpg_wrapper(button_function=GUIButton.set_item_label)
def dpg_set_item_label(tag: str, label: str) -> None:
    return dpg.set_item_label(tag, label=label)


@dpg_wrapper(button_function=GUIButton.set_value)
def dpg_set_value(tag: str, value: Any) -> None:
    return dpg.set_value(tag, value=value)
