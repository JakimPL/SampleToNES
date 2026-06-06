from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.categories.elements.global_ import GraphElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TAG_SEPARATOR
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.graphs import (
    SUF_GRAPH_THEME,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.ui.elements.graphs.graph import GUIGraph
from sampletones_application.ui.elements.graphs.layers.spectrum import SpectrumLayer
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.dpg import (
    dpg_bind_item_theme,
    dpg_delete_children,
)
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE
from sampletones_core.constants.general import MIN_FREQUENCY
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Color, Sender


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
        label: str = "",
    ) -> None:
        self._layout = layout

        self._lbl_axis_x = language_manager[
            Page.GLOBAL,
            Panel.GRAPH,
            TextType.LABEL,
            GraphElements.SPECTRUM_X_AXIS,
        ]
        self._lbl_axis_frequency = language_manager[
            Page.GLOBAL,
            Panel.GRAPH,
            TextType.LABEL,
            GraphElements.SPECTRUM_FREQUENCY_AXIS,
        ]
        self._lbl_spectrum_name = language_manager[
            Page.GLOBAL,
            Panel.GRAPH,
            TextType.LABEL,
            GraphElements.SPECTRUM_NAME,
        ]
        self._msg_navigation = language_manager[
            Page.GLOBAL,
            Panel.GRAPH,
            TextType.MESSAGE,
            GraphElements.SPECTRUM_NAVIGATION,
        ]

        _label = (
            label
            if label
            else language_manager[
                Page.GLOBAL,
                Panel.GRAPH,
                TextType.LABEL,
                GraphElements.SPECTRUM_DISPLAY,
            ]
        )

        self.spectrum: Optional[np.ndarray] = None
        self.frequencies: Optional[np.ndarray] = None
        self.current_library_fragment: Optional[InstructionLibraryFragment[Any]] = None

        self.themes: Dict[Color, str] = {}

        super().__init__(
            tag,
            parent,
            layout.dimensions.width,
            layout.dimensions.height,
            _label,
            (layout.graph.min_x, layout.graph.max_x),
            (MIN_FREQUENCY, DEFAULT_SAMPLE_RATE / 2),
            layout.waveform.zoom_factor,
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
                label=self._lbl_axis_x,
                no_tick_labels=True,
                no_tick_marks=True,
                no_label=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                label=self._lbl_axis_frequency,
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
                name=self._lbl_spectrum_name,
                sample_rate=sample_rate,
                frame_length=frame_length,
                max_display_bins=self._layout.spectrum.max_display_bins,
            )
        )

        self._update_ranges()

    def _on_hover(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        GUIStatusBar.set(self._msg_navigation)

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

        theme_tag = f"{self.tag}{SUF_GRAPH_THEME}{TAG_SEPARATOR}{color[0]}_{color[1]}_{color[2]}_{color[3]}"
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
                series_tag = f"{self.y_axis_tag}{TAG_SEPARATOR}{layer.name.replace(' ', '_')}_{index}".lower()
                dpg.add_bar_series(
                    x=[self._layout.graph.max_x],
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
