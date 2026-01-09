from typing import Any, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones.constants.general import MIN_FREQUENCY
from sampletones.library import InstructionLibraryFragment
from sampletones.typehints import Color, Sender

from ...constants.graphs import (
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_PLOT_AXIS_SPECTRUM_FREQUENCY,
    LBL_PLOT_AXIS_SPECTRUM_X,
    LBL_PLOT_LABEL_SPECTRUM,
    LBL_PLOT_NAME_SPECTRUM,
    MSG_STATUS_SPECTRUM_NAVIGATION,
    SUF_GRAPH_THEME,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_X,
)
from ...utils.dpg import dpg_bind_item_theme, dpg_delete_children
from ..status import GUIStatusBar
from .graph import GUIGraph
from .layers.spectrum import SpectrumLayer


class GUISpectrumGraph(GUIGraph[SpectrumLayer]):
    tag: str
    parent: str
    width: int
    height: int
    label: str

    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_WIDTH,
        height: int = DIM_GRAPH_HEIGHT,
        label: str = LBL_PLOT_LABEL_SPECTRUM,
        x_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_X, VAL_MAX_GRAPH_DEFAULT_X),
        y_range: Tuple[float, float] = (MIN_FREQUENCY, DEFAULT_SAMPLE_RATE / 2),
    ) -> None:
        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.current_library_fragment: Optional[InstructionLibraryFragment[Any]] = None

        self.themes: Dict[Color, str] = {}

        super().__init__(
            tag,
            parent,
            width,
            height,
            label,
            x_range,
            y_range,
        )

    def _create_content(self) -> None:
        with dpg.plot(
            label=self.label,
            tag=self.plot_tag,
            parent=self.tag,
            width=self.width,
            height=self.height,
            anti_aliased=True,
            no_mouse_pos=True,
            fit_button=False,
            pan_button=-1,
        ):
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.x_axis_tag,
                parent=self.plot_tag,
                label=LBL_PLOT_AXIS_SPECTRUM_X,
                no_tick_labels=True,
                no_tick_marks=True,
                no_label=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                label=LBL_PLOT_AXIS_SPECTRUM_FREQUENCY,
                parent=self.plot_tag,
                scale=dpg.mvPlotScale_Log10,
            )

        self._bind_event_handler()
        self._update_axes_limits()

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
                data=fragment,
                name=LBL_PLOT_NAME_SPECTRUM,
                sample_rate=sample_rate,
                frame_length=frame_length,
            )
        )

        self._update_ranges()

    def _on_hover(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        GUIStatusBar.set(MSG_STATUS_SPECTRUM_NAVIGATION)

    def _update_ranges(self) -> None:
        if not self.layers:
            self.y_range = MIN_FREQUENCY, DEFAULT_SAMPLE_RATE / 2
        else:
            frequencies = [frequency for layer in self.layers.values() for frequency, _, _ in layer]
            self.y_range = (frequencies[0], frequencies[-1])

    def _create_brightness_theme(self, color: Color, brightness: float) -> str:
        color = (color[0], color[1], color[2], round(brightness))
        if color in self.themes:
            return self.themes[color]

        theme_tag = f"{self.tag}{SUF_GRAPH_THEME}_{color[0]}_{color[1]}_{color[2]}_{color[3]}"
        with dpg.theme(tag=theme_tag):
            with dpg.theme_component(dpg.mvBarSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Fill,
                    color,
                    category=dpg.mvThemeCat_Plots,
                )

        self.themes[color] = theme_tag
        return theme_tag

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_children(self.y_axis_tag)
        for layer in self.layers.values():
            for index, (frequency, band_width, brightness) in enumerate(layer):
                series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}_{index}".lower()
                dpg.add_bar_series(
                    x=[VAL_MAX_GRAPH_DEFAULT_X],
                    y=[frequency],
                    label="",
                    parent=self.y_axis_tag,
                    tag=series_tag,
                    weight=band_width,
                    horizontal=True,
                )

                theme_tag = self._create_brightness_theme(layer.color, brightness)
                dpg_bind_item_theme(series_tag, theme_tag)

        self._update_ranges()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, *self.x_range)
        dpg.set_axis_limits(self.y_axis_tag, *self.y_range)
