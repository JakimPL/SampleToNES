from typing import Any

from ..utils.dpg import dpg_delete_item
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_panel()

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
