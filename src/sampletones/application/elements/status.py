from __future__ import annotations

from typing import Any, Callable, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

from ..constants.general import (
    SUF_HANDLER_STATUS,
    TAG_STATUS_BAR,
    TAG_STATUS_WINDOW,
    VAL_STATUS_BAR_DISPLAY_TIME,
)
from ..themes.status import StatusBarTheme
from ..utils.dpg import dpg_configure_item, dpg_is_item_hovered
from .button import GUIButton


class GUIStatusBar:
    _REGISTRY: Optional[GUIStatusBar] = None

    def __new__(cls) -> GUIStatusBar:
        if cls._REGISTRY is None:
            cls._REGISTRY = super(GUIStatusBar, cls).__new__(cls)

        return cls._REGISTRY

    def __init__(
        self,
        tag: str = TAG_STATUS_BAR,
        parent: str = TAG_STATUS_WINDOW,
    ) -> None:
        self.tag = tag
        self.parent = parent

        self.message: Optional[str] = None
        self.theme = StatusBarTheme()
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

        self.theme.bind_to_item(TAG_STATUS_WINDOW)

    def update(
        self,
        message: Optional[str] = None,
        delta_time: Optional[float] = None,
    ) -> None:
        if message is not None:
            self.message = message
            self.timer = VAL_STATUS_BAR_DISPLAY_TIME

        dpg_configure_item(self.tag, label=self.message)
        if self.timer > 0.0 and delta_time is not None:
            self.timer -= delta_time
        else:
            self.message = ""
            self.timer = 0.0

    @classmethod
    def set(cls, message: str) -> None:
        if cls._REGISTRY is not None:
            cls._REGISTRY.update(message=message, delta_time=0.0)

    @classmethod
    def bind_to_item(
        cls,
        tag: str,
        message_or_function: Union[str, Callable[[], str]],
    ) -> Optional[str]:
        message_function: Callable[[], str]
        if isinstance(message_or_function, str):

            def message_function() -> str:
                return message_or_function

        elif callable(message_or_function):
            message_function = message_or_function
        else:
            raise TypeError("message_or_function must be a string or a callable returning a string.")

        if cls._REGISTRY is not None:
            handler_tag = f"{tag}{SUF_HANDLER_STATUS}"

            def on_mouse_action(sender: Sender, app_data: Any, user_data: str) -> None:
                if dpg_is_item_hovered(tag):
                    message = message_function()
                    cls.set(message)

            with dpg.handler_registry(tag=handler_tag):
                dpg.add_mouse_move_handler(callback=on_mouse_action)

            return handler_tag

        return None
