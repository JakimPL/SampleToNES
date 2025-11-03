from pathlib import Path

import dearpygui.dearpygui as dpg
import numpy as np

from browser.graphs.bar import GUIBarPlotDisplay
from browser.panels.panel import GUIPanel
from constants.browser import (
    CLR_BAR_PLOT_PITCH,
    DIM_BAR_PLOT_DEFAULT_HEIGHT,
    LBL_RECONSTRUCTION_DETAILS,
    LBL_RECONSTRUCTION_PITCH_PLOT,
    MSG_RECONSTRUCTION_NO_SELECTION,
    TAG_RECONSTRUCTION_DETAILS_PANEL,
    TAG_RECONSTRUCTION_PANEL_GROUP,
    TAG_RECONSTRUCTION_PITCH_BAR_PLOT,
    VAL_BAR_PLOT_PITCH_Y_MAX,
    VAL_BAR_PLOT_PITCH_Y_MIN,
    VAL_PLOT_WIDTH_FULL,
)
from constants.enums import FeatureKey
from reconstructor.reconstruction import Reconstruction


class GUIReconstructionDetailsPanel(GUIPanel):
    def __init__(self) -> None:
        self.pitch_bar_plot: GUIBarPlotDisplay
        self.info_tag = f"{TAG_RECONSTRUCTION_DETAILS_PANEL}_info"

        super().__init__(
            tag=TAG_RECONSTRUCTION_DETAILS_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent_tag, autosize_x=True, autosize_y=True):
            dpg.add_text(LBL_RECONSTRUCTION_DETAILS)
            dpg.add_separator()
            dpg.add_text(MSG_RECONSTRUCTION_NO_SELECTION, tag=self.info_tag)

            self._create_pitch_bar_plot()

    def _create_pitch_bar_plot(self) -> None:
        self.pitch_bar_plot = GUIBarPlotDisplay(
            tag=TAG_RECONSTRUCTION_PITCH_BAR_PLOT,
            parent=self.tag,
            width=VAL_PLOT_WIDTH_FULL,
            height=DIM_BAR_PLOT_DEFAULT_HEIGHT,
            label=LBL_RECONSTRUCTION_PITCH_PLOT,
            y_min=VAL_BAR_PLOT_PITCH_Y_MIN,
            y_max=VAL_BAR_PLOT_PITCH_Y_MAX,
        )

    def display_reconstruction(self, reconstruction: Reconstruction) -> None:
        dpg.set_value(self.info_tag, "")

        exported_features = reconstruction.export(as_string=False)

        for generator_name, features in exported_features.items():
            if FeatureKey.HI_PITCH in features:
                pitch_data = features[FeatureKey.HI_PITCH]
                if isinstance(pitch_data, np.ndarray):
                    self.pitch_bar_plot.load_data(
                        data=pitch_data,
                        name=f"{generator_name} - HI_PITCH",
                        color=CLR_BAR_PLOT_PITCH,
                    )
                    break

    def clear_display(self) -> None:
        dpg.set_value(self.info_tag, MSG_RECONSTRUCTION_NO_SELECTION)
        self.pitch_bar_plot.clear_layers()
