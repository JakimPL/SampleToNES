from pathlib import Path

import dearpygui.dearpygui as dpg

from browser.panels.panel import GUIPanel
from constants.browser import (
    LBL_RECONSTRUCTION_DETAILS,
    MSG_RECONSTRUCTION_NO_SELECTION,
    TAG_RECONSTRUCTION_DETAILS_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
)
from reconstructor.reconstruction import Reconstruction


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        super().__init__(
            tag=TAG_RECONSTRUCTION_DETAILS_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
            init=False,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent_tag, autosize_x=True, autosize_y=True):
            dpg.add_text(LBL_RECONSTRUCTION_DETAILS)
            dpg.add_separator()
            dpg.add_text(MSG_RECONSTRUCTION_NO_SELECTION)

    def display_reconstruction(self, reconstruction: Reconstruction) -> None:
        pass

    def clear_display(self) -> None:
        pass
