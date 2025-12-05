from typing import Any

import dearpygui.dearpygui as dpg

from ..utils.dpg import dpg_delete_item
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def center(self) -> None:
        width, height = dpg.get_item_rect_size(self.tag)
        x = (dpg.get_viewport_width() - width) / 2
        y = (dpg.get_viewport_height() - height) / 2
        dpg.set_item_pos(self.tag, [x, y])

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()
        dpg.set_frame_callback(dpg.get_frame_count() + 1, self.center)

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
