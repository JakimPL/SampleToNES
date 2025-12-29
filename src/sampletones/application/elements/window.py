from typing import Any

import dearpygui.dearpygui as dpg

from ..utils.dialogs import get_center
from ..utils.dpg import dpg_delete_item, dpg_set_frame_callback
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def center(self) -> None:
        width, height = dpg.get_item_rect_size(self.tag)
        x, y = get_center(width, height)
        dpg.set_item_pos(self.tag, [x, y])

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()
        dpg_set_frame_callback(self.center)

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
