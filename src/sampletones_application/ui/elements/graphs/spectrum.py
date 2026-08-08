from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import SUF_GRAPH_THEME
from sampletones_application.ui.elements.graphs.graph import GUIGraph
from sampletones_application.ui.elements.graphs.layers.spectrum import SpectrumLayer
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dpg import (
    dpg_bind_item_theme,
    dpg_delete_children,
)
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.blended import BlendedColor
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.general import MIN_FREQUENCY
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Sender
from sampletones_shared.utils.color import MAX_CHANNEL_VALUE


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
        *,
        layout: GraphsLayout,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
    ) -> None:
        self._language_manager = language_manager
        self._layout = layout
        self._status_bar = status_bar

        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None

        self.themes: Dict[BaseColor, str] = {}

        super().__init__(
            tag,
            parent,
            layout.dimensions.width,
            layout.dimensions.height,
            "",
            x_range=(layout.graph.min_x, layout.graph.max_x),
            y_range=(MIN_FREQUENCY, DEFAULT_SAMPLE_RATE / 2),
            zoom_factor=layout.waveform.zoom_factor,
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
                label=self._language_manager["global.graph.label.spectrum_x_axis"],
                no_tick_labels=True,
                no_tick_marks=True,
                no_label=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                label=self._language_manager["global.graph.label.spectrum_frequency_axis"],
                parent=self.plot_tag,
                scale=dpg.mvPlotScale_Log10,
            )

        self._bind_event_handler()
        self._update_axes_limits()

    def load_library_fragment(
        self,
        fragment: InstructionLibraryFragment[Any],
        _sample_rate: int,
        _frame_length: int,
    ) -> None:
        self.clear_layers()

        self.add_layer(
            SpectrumLayer(
                data=fragment,
                name=self._language_manager["global.graph.label.spectrum_name"],
                max_display_bins=self._layout.spectrum.max_display_bins,
                color_dim=self._layout.spectrum.color_dim,
                color_bright=self._layout.spectrum.color_bright,
            )
        )

        self._update_ranges()

    def _on_hover(
        self,
        _sender: Sender,
        _app_data: Any,
        _user_data: Any,
    ) -> None:
        self._status_bar.set(self._language_manager["global.graph.message.spectrum_navigation"])

    def _update_ranges(self) -> None:
        if not self.layers:
            self.y_range = MIN_FREQUENCY, DEFAULT_SAMPLE_RATE / 2
        else:
            frequencies = [frequency for layer in self.layers.values() for frequency, _, _ in layer]
            self.y_range = (frequencies[0], frequencies[-1])

    def _create_brightness_theme(
        self,
        color_dim: BaseColor,
        color_bright: BaseColor,
        brightness: float,
    ) -> str:
        """The theme filling a band at ``brightness``, built once per shade the spectrum shows.

        A band's shade sits on the gradient between the dim and bright ends, and is held as the
        blend of the two tokens rather than as the value it currently reads, so every band the
        spectrum has drawn takes the new gradient when another palette is activated.
        """
        color = BlendedColor(
            start=color_dim,
            end=color_bright,
            fraction=brightness / MAX_CHANNEL_VALUE,
        )
        if color in self.themes:
            return self.themes[color]

        theme_tag = compose_tag(self.tag, SUF_GRAPH_THEME, str(len(self.themes)))
        with dpg.theme(tag=theme_tag):
            with dpg.theme_component(dpg.mvBarSeries):
                dpg_add_palette_theme_color(
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
                series_tag = compose_tag(self.y_axis_tag, f"{layer.name}_{index}")
                dpg.add_bar_series(
                    x=[self._layout.graph.max_x],
                    y=[frequency],
                    label="",
                    parent=self.y_axis_tag,
                    tag=series_tag,
                    weight=band_width,
                    horizontal=True,
                )

                theme_tag = self._create_brightness_theme(layer.color_dim, layer.color_bright, brightness)
                dpg_bind_item_theme(series_tag, theme_tag)

        self._update_ranges()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, *self.x_range)
        dpg.set_axis_limits(self.y_axis_tag, *self.y_range)
