from typing import Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from browser.graphs.graph import GUIGraphDisplay
from browser.graphs.layers.spectrum import SpectrumLayer
from constants.browser import (
    DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
    DIM_GRAPH_DEFAULT_WIDTH,
    LBL_SPECTRUM_DISPLAY,
    LBL_SPECTRUM_X_AXIS,
    LBL_SPECTRUM_Y_AXIS,
    VAL_WAVEFORM_AXIS_SLOT,
)
from constants.general import MIN_FREQUENCY, SAMPLE_RATE
from library.data import LibraryFragment


class GUISpectrumDisplay(GUIGraphDisplay):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_DEFAULT_WIDTH,
        height: int = DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
        label: str = LBL_SPECTRUM_DISPLAY,
    ) -> None:
        super().__init__(tag, parent, width, height, label)
        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.current_library_fragment: Optional[LibraryFragment] = None

    def _create_content(self) -> None:
        with dpg.plot(
            label=self.label,
            height=self.height,
            width=self.width,
            tag=self.plot_tag,
            anti_aliased=True,
            no_inputs=True,
            pan_button=-1,
        ):
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_SPECTRUM_X_AXIS, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_SPECTRUM_Y_AXIS, tag=self.y_axis_tag, scale=dpg.mvPlotScale_Log10)
            dpg.set_axis_limits(self.y_axis_tag, MIN_FREQUENCY, SAMPLE_RATE // 2)

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

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

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

                dpg.bind_item_theme(series_tag, bar_theme)

    def _update_axes_limits(self) -> None:
        if not self.layers:
            return

        frequencies = [frequency for layer in self.layers.values() for frequency, _, _ in layer]
        min_frequency = frequencies[0]
        max_frequency = frequencies[-1]
        dpg.set_axis_limits(self.y_axis_tag, min_frequency, max_frequency)
