from typing import Any

from ..utils.callbacks import CallbackQueue
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
        CallbackQueue.add(self.center, priority=True)

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def prepare(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Subclasses must implement this method")
