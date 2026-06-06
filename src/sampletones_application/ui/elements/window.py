from abc import abstractmethod
from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.dialogs import center_item
from sampletones_application.utils.dpg import dpg_delete_item


class GUIWindow(GUIPanel):
    """``GUIPanel`` variant for modal windows that are recreated on each appearance.

    Unlike a regular panel (which is created once and toggled with
    ``show=True/False``), a ``GUIWindow`` is fully deleted from DPG when hidden
    and rebuilt from scratch when shown.  This is appropriate for dialogs and
    pop-ups whose content depends on runtime context (e.g. a "Save as" dialog
    pre-filled with the current filename).

    Responsibilities:
    - Delete the old widget tree on ``hide()`` (via ``dpg_delete_item``).
    - Call ``prepare(*args, **kwargs)`` to set instance state that
      ``create_panel()`` depends on, then rebuild the widget tree on ``show()``.
    - Centre the window on screen after creation.

    Governing principles:
    - The two-step ``prepare`` → ``create_panel`` sequence replaces the
      single-step ``create_panel`` of ``GUIPanel``.  Subclasses must implement
      ``prepare`` to store any arguments needed by ``create_panel``.
    - All other ``GUIPanel`` principles apply: no domain state, no direct
      coordinator calls, DPG confined to ``create_panel()``.

    Dependencies: ``center_item`` (from ``utils/dialogs``),
    ``dpg_delete_item`` (from ``utils/dpg``).
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
