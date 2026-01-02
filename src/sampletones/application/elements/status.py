from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones.application.elements.button import GUIButton

from ..constants.general import (
    TAG_STATUS_BAR,
    TAG_STATUS_WINDOW,
    VAL_STATUS_BAR_DISPLAY_TIME,
)
from ..themes.status import StatusBarTheme


class GUIStatusBar:
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

        dpg.set_value(self.tag, self.message)
        if self.timer > 0.0 and delta_time is not None:
            self.timer -= delta_time
        else:
            self.message = ""
            self.timer = 0.0
