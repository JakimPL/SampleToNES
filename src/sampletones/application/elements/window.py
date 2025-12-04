from typing import Any

import dearpygui.dearpygui as dpg

from ..utils.dpg import dpg_configure_item, dpg_delete_item
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def center(self) -> None:
        width = dpg.get_item_width(self.tag)
        height = dpg.get_item_height(self.tag)
        assert width is not None, f"Width of {self.tag} is None"
        assert height is not None, f"Height of {self.tag} is None"
        x = dpg.get_viewport_width() - width
        y = dpg.get_viewport_height() - height
        dpg_configure_item(self.tag, pos=(x // 2, y // 2))

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()
        self.center()

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
