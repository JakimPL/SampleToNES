import functools
from typing import (
    Any,
    Callable,
    Concatenate,
    Optional,
    ParamSpec,
    TypeVar,
    cast,
)

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.button import GUIButton
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback

P = ParamSpec("P")
R = TypeVar("R")


def dpg_wrapper(
    button_function: Optional[Callback] = None,
) -> Callable[
    [Callable[Concatenate[Sender, P], Optional[R]]],
    Callable[Concatenate[Sender, P], Optional[R]],
]:
    def decorator(
        function: Callable[Concatenate[Sender, P], Optional[R]],
    ) -> Callable[Concatenate[Sender, P], Optional[R]]:
        @functools.wraps(function)
        def wrapper(tag: Sender, *args: P.args, **kwargs: P.kwargs) -> Optional[R]:
            if button_function is not None and GUIButton.exists(tag):
                if dpg.does_item_exist(tag):
                    button = GUIButton.get(tag)
                    if button is not None:
                        button_function(button, *args, **kwargs)
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


def dpg_delete_children(tag: Sender, /, *_args: Any, **kwargs: Any) -> None:
    dpg_delete_item(tag, children_only=True, **kwargs)


def dpg_bind_item_theme(
    tag: Sender,
    theme_tag: Sender,
    /,
    *args: Any,
    **kwargs: Any,
) -> None:
    if dpg.does_item_exist(tag) and dpg.does_item_exist(theme_tag):
        dpg.bind_item_theme(tag, theme_tag, *args, **kwargs)


def dpg_get_item_parent(
    tag: Sender,
    /,
    *args: Any,
    **kwargs: Any,
) -> Optional[Sender]:
    """The item's parent, or None when the item is absent.

    Queued callbacks mutate the item tree on the callback-queue thread, so an item read
    from another thread can be removed underneath this lookup; DearPyGui reports the
    absent item by raising, which resolves here to None.
    """
    try:
        parent: Optional[Sender] = dpg.get_item_parent(tag, *args, **kwargs)
    except Exception:
        return None

    return parent


@dpg_wrapper(button_function=GUIButton.configure_item)
def dpg_configure_item(tag: Sender, /, *args: Any, **kwargs: Any) -> None:
    dpg.configure_item(tag, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.set_item_callback)
def dpg_set_item_callback(
    tag: Sender,
    callback: Callback,
    /,
    *args: Any,
    **kwargs: Any,
) -> None:
    dpg.set_item_callback(tag, callback=callback, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.set_item_label)
def dpg_set_item_label(
    tag: Sender,
    /,
    label: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    dpg.set_item_label(tag, label=label, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.get_item_label)
def dpg_get_item_label(
    tag: Sender,
    /,
    *args: Any,
    **kwargs: Any,
) -> Optional[str]:
    item_label: Optional[str] = dpg.get_item_label(tag, *args, **kwargs)
    return item_label


@dpg_wrapper(button_function=GUIButton.set_value)
def dpg_set_value(
    tag: Sender,
    value: Any,
    /,
    *args: Any,
    **kwargs: Any,
) -> None:
    dpg.set_value(tag, value, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.get_value)
def dpg_get_value(tag: Sender, /, *args: Any, **kwargs: Any) -> Any:
    return dpg.get_value(tag, *args, **kwargs)


@dpg_wrapper(button_function=GUIButton.is_item_hovered)
def dpg_is_item_hovered(
    tag: Sender,
    /,
    *args: Any,
    **kwargs: Any,
) -> Optional[bool]:
    is_hovered: Optional[bool] = dpg.is_item_hovered(tag, *args, **kwargs)
    return is_hovered
