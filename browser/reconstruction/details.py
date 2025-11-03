from pathlib import Path

import dearpygui.dearpygui as dpg

from browser.graphs.bar import GUIBarPlotDisplay
from browser.panels.panel import GUIPanel
from browser.reconstruction.feature import FeatureData
from constants.browser import (
    CLR_BAR_PLOT_PITCH,
    DIM_BAR_PLOT_DEFAULT_HEIGHT,
    LBL_RECONSTRUCTION_DETAILS,
    LBL_RECONSTRUCTION_PITCH_PLOT,
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

        super().__init__(
            tag=TAG_RECONSTRUCTION_DETAILS_PANEL,
            parent_tag=TAG_RECONSTRUCTION_PANEL_GROUP,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, parent=self.parent_tag, autosize_x=True, autosize_y=True):
            dpg.add_text(LBL_RECONSTRUCTION_DETAILS)
            dpg.add_separator()

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
        feature_data = FeatureData.load(reconstruction)

        generator_name = feature_data.get_first_generator_with_feature(FeatureKey.HI_PITCH)
        if generator_name:
            pitch_data = feature_data.get_feature_for_generator(generator_name, FeatureKey.HI_PITCH)
            if pitch_data is not None:
                self.pitch_bar_plot.load_data(
                    data=pitch_data,
                    name=f"{generator_name} - HI_PITCH",
                    color=CLR_BAR_PLOT_PITCH,
                )

    def clear_display(self) -> None:
        self.pitch_bar_plot.clear_layers()
