from abc import abstractmethod
from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.gui.dialogs import center_item
from sampletones_application.utils.gui.dpg import dpg_delete_item


class GUIWindow(GUIPanel):
    """
    A ``GUIPanel`` whose widget tree is rebuilt on each appearance.

    Unlike a standard panel, it is fully deleted from DPG when hidden and
    recreated when shown — appropriate when content depends on runtime context.
    The ``prepare`` step captures arguments before the previous tree is torn
    down.
    """

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
