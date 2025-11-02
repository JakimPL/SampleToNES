from pathlib import Path

import dearpygui.dearpygui as dpg

from browser.panel import GUIPanel
from constants.browser import (
    LBL_RECONSTRUCTION_EXPORT,
    TAG_RECONSTRUCTION_EXPORT_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
)
from reconstructor.reconstruction import Reconstruction


class GUIReconstructionExportPanel(GUIPanel):
    def __init__(self) -> None:
        super().__init__(
            tag=TAG_RECONSTRUCTION_EXPORT_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
            init=False,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent_tag, autosize_x=True, autosize_y=True):
            dpg.add_text(LBL_RECONSTRUCTION_EXPORT)
            dpg.add_separator()

    def load_reconstruction(self, reconstruction: Reconstruction) -> None:
        pass

    def clear(self) -> None:
        pass
