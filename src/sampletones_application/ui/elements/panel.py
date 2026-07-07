from abc import ABC, abstractmethod

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
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

    def _create_section_header(self, label: str) -> None:
        """Render this panel's section header: its title in the bold section font.

        Every panel opens with the same header treatment, so defining it on the base
        keeps the tabs consistent and gives one place to restyle every header at once.
        """
        section_text = dpg.add_text(label)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def set_visibility(self, visible: bool) -> None:
        dpg_configure_item(self.tag, show=visible)

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)
