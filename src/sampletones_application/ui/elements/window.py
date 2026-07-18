from abc import abstractmethod
from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG_WINDOW
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.align import center_item
from sampletones_application.utils.gui.dpg import dpg_delete_item


class GUIWindow(GUIPanel):
    """
    A ``GUIPanel`` whose widget tree is rebuilt on each appearance.

    Unlike a standard panel, it is fully deleted from DPG when hidden and
    recreated when shown — appropriate when content depends on runtime context.
    The ``prepare`` step captures arguments before the previous tree is torn
    down. Each rebuild binds the elevated dialog-window theme so the window
    floats above the app with an accent border and title bar.
    """

    def center(self) -> None:
        center_item(self.tag)

    def show(self, *args: Any, **kwargs: Any) -> None:
        self.hide()
        self.prepare(*args, **kwargs)
        self.create_window()
        ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG_WINDOW).bind_to_item(self.tag)
        dpg.split_frame()
        self.center()

    def hide(self) -> None:
        dpg_delete_item(self.tag)

    def create_panel(self, parent: str) -> None:
        """Satisfy the panel contract for a top-level window, which owns its own
        ``dpg.window`` and builds through ``create_window``."""
        self.create_window()

    @abstractmethod
    def create_window(self) -> None: ...

    @abstractmethod
    def prepare(self, *args: Any, **kwargs: Any) -> None: ...
