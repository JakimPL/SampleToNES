from typing import Any, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.general import DEFAULT_SAMPLE_RATE, MIN_FREQUENCY
from sampletones.library import InstructionLibraryFragment

from ...constants.graphs import (
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_PLOT_AXIS_SPECTRUM_FREQUENCY,
    LBL_PLOT_AXIS_SPECTRUM_X,
    LBL_PLOT_LABEL_SPECTRUM,
    LBL_PLOT_NAME_SPECTRUM,
    SUF_GRAPH_THEME,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_X,
)
from ...utils.dpg import dpg_bind_item_theme, dpg_delete_children, dpg_delete_item
from .graph import GUIGraph
from .layers.spectrum import SpectrumLayer


class GUISpectrumGraph(GUIGraph):
    tag: str
    parent: str
    width: int
    height: int
    label: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_WIDTH,
        height: int = DIM_GRAPH_HEIGHT,
        label: str = LBL_PLOT_LABEL_SPECTRUM,
        x_min: float = VAL_MIN_GRAPH_DEFAULT_X,
        x_max: float = VAL_MAX_GRAPH_DEFAULT_X,
        y_min: float = MIN_FREQUENCY,
        y_max: float = DEFAULT_SAMPLE_RATE / 2,
    ) -> None:
        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.current_library_fragment: Optional[InstructionLibraryFragment[Any]] = None

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
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_PLOT_AXIS_SPECTRUM_X, tag=self.x_axis_tag)
            dpg.add_plot_axis(
                dpg.mvYAxis,
                label=LBL_PLOT_AXIS_SPECTRUM_FREQUENCY,
                tag=self.y_axis_tag,
                scale=dpg.mvPlotScale_Log10,
            )

    def load_library_fragment(
        self,
        fragment: InstructionLibraryFragment[Any],
        sample_rate: int,
        frame_length: int,
    ) -> None:
        self.clear_layers()
        self.current_library_fragment = fragment

        self.add_layer(
            SpectrumLayer(
                fragment=fragment,
                name=LBL_PLOT_NAME_SPECTRUM,
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
                theme_tag = f"{series_tag}{SUF_GRAPH_THEME}"
                dpg.add_bar_series(
                    x=[self.x_max],
                    y=[frequency],
                    label="",
                    parent=self.y_axis_tag,
                    tag=series_tag,
                    weight=band_width,
                    horizontal=True,
                )

                dpg_delete_item(theme_tag)
                with dpg.theme(tag=theme_tag):
                    with dpg.theme_component(dpg.mvBarSeries):
                        dpg.add_theme_color(
                            dpg.mvPlotCol_Fill,
                            (*layer.color, brightness),
                            category=dpg.mvThemeCat_Plots,
                        )

                dpg_bind_item_theme(series_tag, theme_tag)

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        if not self.layers:
            dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
            return

        frequencies = [frequency for layer in self.layers.values() for frequency, _, _ in layer]
        self.y_min = frequencies[0]
        self.y_max = frequencies[-1]
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
