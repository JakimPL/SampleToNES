from typing import Optional

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.general import MIN_FREQUENCY, SAMPLE_RATE
from sampletones.library import LibraryFragment

from ...constants import (
    DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
    DIM_GRAPH_DEFAULT_WIDTH,
    LBL_SPECTRUM_DISPLAY,
    LBL_SPECTRUM_X_AXIS,
    LBL_SPECTRUM_Y_AXIS,
    VAL_GRAPH_DEFAULT_X_MAX,
    VAL_GRAPH_DEFAULT_X_MIN,
)
from ...utils.common import dpg_bind_item_theme, dpg_delete_children
from .graph import GUIGraphDisplay
from .layers.spectrum import SpectrumLayer


class GUISpectrumDisplay(GUIGraphDisplay):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_DEFAULT_WIDTH,
        height: int = DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
        label: str = LBL_SPECTRUM_DISPLAY,
        x_min: float = VAL_GRAPH_DEFAULT_X_MIN,
        x_max: float = VAL_GRAPH_DEFAULT_X_MAX,
        y_min: float = MIN_FREQUENCY,
        y_max: float = SAMPLE_RATE / 2,
    ) -> None:
        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.current_library_fragment: Optional[LibraryFragment] = None

        super().__init__(
            tag,
            parent,
            width,
            height,
            label,
            x_min,
            x_max,
            y_min,
            y_max,
        )

    def _create_content(self) -> None:
        with dpg.plot(
            label=self.label,
            width=self.width,
            height=self.height,
            tag=self.plot_tag,
            anti_aliased=True,
            no_inputs=True,
            pan_button=-1,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_SPECTRUM_X_AXIS, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_SPECTRUM_Y_AXIS, tag=self.y_axis_tag, scale=dpg.mvPlotScale_Log10)

    def load_library_fragment(
        self,
        fragment: LibraryFragment,
        sample_rate: int,
        frame_length: int,
    ) -> None:
        self.clear_layers()
        self.current_library_fragment = fragment

        self.add_layer(
            SpectrumLayer(
                fragment=fragment,
                name="Spectrum Layer",
                sample_rate=sample_rate,
                frame_length=frame_length,
            )
        )

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_children(self.y_axis_tag)
        self._update_axes_limits()
        for layer in self.layers.values():
            for index, (frequency, band_width, brightness) in enumerate(layer):
                series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}_{index}"
                dpg.add_bar_series(
                    x=[self.x_max],
                    y=[frequency],
                    label="",
                    parent=self.y_axis_tag,
                    tag=series_tag,
                    weight=band_width,
                    horizontal=True,
                )
                with dpg.theme() as bar_theme:
                    with dpg.theme_component(dpg.mvBarSeries):
                        dpg.add_theme_color(
                            dpg.mvPlotCol_Fill,
                            (*layer.color, brightness),
                            category=dpg.mvThemeCat_Plots,
                        )

                dpg_bind_item_theme(series_tag, bar_theme)

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        if not self.layers:
            dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
            return

        frequencies = [frequency for layer in self.layers.values() for frequency, _, _ in layer]
        self.y_min = frequencies[0]
        self.y_max = frequencies[-1]
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
