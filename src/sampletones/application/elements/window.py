from typing import Any

from ..utils.dpg import dpg_delete_item
from .panel import GUIPanel


class GUIWindow(GUIPanel):
    def show(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def hide(self) -> None:
        dpg_delete_item(self.tag)
