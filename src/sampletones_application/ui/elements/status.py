from __future__ import annotations

from typing import Any, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import (
    SUF_HANDLER_STATUS,
    TAG_GLOBAL_STATUS_BAR,
    TAG_GLOBAL_STATUS_WINDOW,
    TAG_GLOBAL_THEME_STATUS,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_item,
    dpg_is_item_hovered,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback


class GUIStatusBar:
    def __init__(
        self,
        tag: str = TAG_GLOBAL_STATUS_BAR,
        parent: str = TAG_GLOBAL_STATUS_WINDOW,
        display_time: float = 2.0,
    ) -> None:
        self.tag = tag
        self.parent = parent
        self._display_time = display_time

        self.message: Optional[str] = None
        self.theme = ThemeRegistry.get(TAG_GLOBAL_THEME_STATUS)
        self.timer = 0.0

    def create(self) -> None:
        with dpg.menu_bar(parent=self.parent):
            GUIButton(
                label="",
                tag=self.tag,
                width=-1,
                enabled=False,
                theme=self.theme,
                indent=0,
            )

        self.theme.bind_to_item(TAG_GLOBAL_STATUS_WINDOW)

    @staticmethod
    def get_message(
        message_or_function: Union[str, MessageCallback],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if isinstance(message_or_function, str):
            return message_or_function

        if callable(message_or_function):
            return message_or_function(*args, **kwargs)

        raise TypeError("'message_or_function' must be a string or a callable returning a string")

    def update(
        self,
        *args: Any,
        message_or_function: Optional[Union[str, MessageCallback]] = None,
        delta_time: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        if message_or_function is not None:
            self.message = self.get_message(
                message_or_function,
                *args,
                **kwargs,
            )
            self.timer = self._display_time

        dpg_configure_item(self.tag, label=self.message)
        if self.timer > 0.0 and delta_time is not None:
            self.timer -= delta_time
        else:
            self.message = ""
            self.timer = 0.0

    def set(
        self,
        message_or_function: Union[str, MessageCallback],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.update(
            *args,
            message_or_function=message_or_function,
            delta_time=0.0,
            **kwargs,
        )

    @staticmethod
    def create_message_function(
        message_or_function: Union[str, MessageCallback],
    ) -> MessageCallback:
        if isinstance(message_or_function, str):

            def message_function(*args: Any, **kwargs: Any) -> str:
                return message_or_function

        elif callable(message_or_function):
            message_function = message_or_function

        else:
            raise TypeError("'message_or_function' must be a string or a callable returning a string.")

        return message_function

    def bind_to_item(
        self,
        tag: str,
        message_or_function: Union[str, MessageCallback],
    ) -> str:
        message_function = self.create_message_function(message_or_function)
        handler_tag = f"{tag}{SUF_HANDLER_STATUS}"
        hover_tag = GUIButton.hover_tag(tag)

        def on_mouse_action(sender: Sender, app_data: Any, user_data: str) -> None:
            if dpg_is_item_hovered(hover_tag):
                message = message_function(sender, app_data, user_data)
                self.set(message)

        dpg_delete_item(handler_tag)
        with dpg.handler_registry(tag=handler_tag):
            dpg.add_mouse_move_handler(callback=on_mouse_action)

        return handler_tag
