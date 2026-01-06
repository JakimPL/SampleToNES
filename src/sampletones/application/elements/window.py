from typing import Any

from ..utils.dialogs import center_item
from ..utils.dpg import dpg_delete_item, dpg_set_frame_callback
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def center(self) -> None:
        center_item(self.tag, self.width, self.height)

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()
        dpg_set_frame_callback(self.center)

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
