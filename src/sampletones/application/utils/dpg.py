import functools
from typing import Any, Callable, Concatenate, Optional, ParamSpec, TypeVar, cast

import dearpygui.dearpygui as dpg

from sampletones.typehints import Callback, Sender

from ..elements.button import GUIButton

P = ParamSpec("P")
R = TypeVar("R")


def dpg_wrapper(
    button_function: Optional[Callback] = None,
) -> Callable[[Callable[Concatenate[Sender, P], Optional[R]]], Callable[Concatenate[Sender, P], Optional[R]]]:
    def decorator(
        function: Callable[Concatenate[Sender, P], Optional[R]],
    ) -> Callable[Concatenate[Sender, P], Optional[R]]:
        @functools.wraps(function)
        def wrapper(tag: Sender, *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
            if button_function is not None and tag in GUIButton._REGISTRY:
                if dpg.does_item_exist(tag):
                    button_function(GUIButton._REGISTRY[tag], *args, **kwargs)
                else:
                    GUIButton.delete(tag)
                return None

            if dpg.does_item_exist(tag):
                return function(tag, *args, **kwargs)

            return None

        return cast(Callable[Concatenate[Sender, P], Optional[R]], wrapper)

    return decorator


@dpg_wrapper(button_function=GUIButton.delete_item)
def dpg_delete_item(tag: Sender, /, *args: Any, **kwargs: Any) -> None:
    dpg.delete_item(tag, *args, **kwargs)


def dpg_delete_children(tag: Sender, /, *args: Any, **kwargs: Any) -> None:
    dpg_delete_item(tag, children_only=True)


def dpg_bind_item_theme(tag: Sender, theme_tag: Sender, /, *args: Any, **kwargs: Any) -> None:
    if dpg.does_item_exist(tag) and dpg.does_item_exist(theme_tag):
        dpg.bind_item_theme(tag, theme_tag, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.configure_item)
def dpg_configure_item(tag: Sender, /, *args: Any, **kwargs: Any) -> None:
    dpg.configure_item(tag, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.set_item_callback)
def dpg_set_item_callback(tag: Sender, callback: Callback, /, *args: Any, **kwargs: Any) -> None:
    dpg.set_item_callback(tag, callback=callback, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.set_item_label)
def dpg_set_item_label(tag: Sender, /, label: str, *args: Any, **kwargs: Any) -> None:
    dpg.set_item_label(tag, label=label, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.get_item_label)
def dpg_get_item_label(tag: Sender, /, *args: Any, **kwargs: Any) -> Optional[str]:
    item_label: Optional[str] = dpg.get_item_label(tag, *args, **kwargs)
    return item_label


@dpg_wrapper(button_function=GUIButton.set_value)
def dpg_set_value(tag: Sender, value: Any, /, *args: Any, **kwargs: Any) -> None:
    dpg.set_value(tag, value, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.is_item_hovered)
def dpg_is_item_hovered(tag: Sender, /, *args: Any, **kwargs: Any) -> Optional[bool]:
    is_hovered: Optional[bool] = dpg.is_item_hovered(tag, *args, **kwargs)
    return is_hovered


def dpg_set_frame_callback(
    callback: Callback,
    frame_count: int = 1,
    void_callback=True,
) -> None:
    frame_count = dpg.get_frame_count() + max(1, frame_count)
    if void_callback:

        def wrapper(sender: Sender, app_data: Any, user_data: Any) -> None:
            callback()

    else:
        wrapper = callback

    dpg.set_frame_callback(frame_count, wrapper)
