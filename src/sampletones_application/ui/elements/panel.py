from abc import ABC, abstractmethod

from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.utils.callbacks import CallbackMixin


class GUIPanel(CallbackMixin, ABC):
    """
    The foundation of every visible component in the View layer.

    - State flows in through ``update_view``; user actions flow out through
      ``on_x`` callback hooks.
    - A panel owns its widget subtree and holds no domain state — it knows
      how to display data, not what it means.
    """

    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = 0,
        height: int = 0,
        init: bool = False,
    ) -> None:
        self.tag = tag
        self.parent = parent
        self.width = width
        self.height = height

        if init:
            self.create_panel()

    @abstractmethod
    def create_panel(self) -> None: ...

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
