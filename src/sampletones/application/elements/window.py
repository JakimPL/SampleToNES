from abc import abstractmethod
from typing import Any

import dearpygui.dearpygui as dpg

from ..utils.dialogs import center_item
from ..utils.dpg import dpg_delete_item
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def center(self) -> None:
        center_item(self.tag, self.width, self.height)

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()
        dpg.split_frame()
        self.center()

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    @abstractmethod
    def prepare(self, *args: Any, **kwargs: Any) -> None: ...
