from typing import Any, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones_application.constants.graphs import (
    SUF_GRAPH_THEME,
    SUF_WAVEFORM_OVERLAY,
    SUF_WAVEFORM_POSITION_INDICATOR,
)
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.text.elements.global_ import GraphElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.elements.graphs.graph import GUIGraph
from sampletones_application.ui.elements.graphs.layers.array import ArrayLayer
from sampletones_application.ui.elements.graphs.layers.instruction import InstructionLayer
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.themes.graphs.indicator import IndicatorGraphTheme
from sampletones_application.ui.themes.graphs.overlay import OverlayGraphTheme
from sampletones_application.utils.dpg import (
    dpg_bind_item_theme,
    dpg_configure_item,
    dpg_delete_children,
    dpg_delete_item,
)
from sampletones_application.view_model.reconstruction.data import ReconstructionData
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.library import InstructionLibraryFragment
from sampletones_shared.types.application import Sender


class GUIWaveformGraph(GUIGraph[Union[ArrayLayer, InstructionLayer]]):
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
    ):
        self._layout = layout

        self._lbl_waveform_original = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_ORIGINAL)
        ]
        self._lbl_waveform_reconstruction = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_RECONSTRUCTION)
        ]
        self._lbl_axis_time = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_TIME_AXIS)
        ]
        self._lbl_axis_amplitude = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_AMPLITUDE_AXIS)
        ]
        self._lbl_sample_name = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_SAMPLE_NAME)
        ]
        self._msg_navigation = language_manager[
            TextKey(Page.GLOBAL, Panel.GRAPH, TextType.MESSAGE, GraphElements.WAVEFORM_NAVIGATION)
        ]

        _label = (
            label
            if label
            else language_manager[TextKey(Page.GLOBAL, Panel.GRAPH, TextType.LABEL, GraphElements.WAVEFORM_DISPLAY)]
        )

        self.reconstruction_autoscale = True

        self.position_indicator_tag = f"{tag}{SUF_WAVEFORM_POSITION_INDICATOR}"
        self.overlay_rectangle_tag = f"{tag}{SUF_WAVEFORM_OVERLAY}"

        self.indicator_theme = IndicatorGraphTheme()
        self.overlay_theme = OverlayGraphTheme()

        self.current_data: Optional[Union[InstructionLibraryFragment[Any], ReconstructionData]] = None
        self.current_position: int = 0

        _min_x = layout.graph.min_x
        _max_x = layout.graph.max_x
        _min_y = layout.graph.min_y
        _max_y = layout.graph.max_y

        super().__init__(
            tag,
            parent,
            layout.dimensions.width,
            layout.dimensions.height,
            _label,
            (_min_x, _max_x),
            (_min_y, _max_y),
            layout.waveform.zoom_factor,
        )

    @property
    def sample_length(self) -> int:
        if isinstance(self.current_data, InstructionLibraryFragment):
            return len(self.current_data.data)

        if isinstance(self.current_data, ReconstructionData):
            return len(self.current_data.reconstruction.approximation)

        return 0

    def _create_content(self) -> None:
        _min_y = self._layout.graph.min_y
        _max_y = self._layout.graph.max_y

        with dpg.plot(
            label=self.label,
            tag=self.plot_tag,
            parent=self.tag,
            width=self.width,
            height=self.height,
            anti_aliased=True,
            no_mouse_pos=True,
            no_box_select=True,
            fit_button=False,
            horizontal_mod=dpg.mvKey_LShift,
            pan_button=dpg.mvMouseButton_Left,
            zoom_rate=self.zoom_factor,
        ):
            dpg.add_plot_legend(tag=self.legend_tag, parent=self.plot_tag, location=dpg.mvPlot_Location_NorthEast)
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.x_axis_tag,
                parent=self.plot_tag,
                label=self._lbl_axis_time,
                no_label=True,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                parent=self.plot_tag,
                label=self._lbl_axis_amplitude,
            )
            self._add_position_indicator()
            self._set_overlay_rectangle()

        self._bind_event_handler()
        self._update_axes_limits()

    def set_overlay_range(self, start: float = 0.0, end: float = 0.0) -> None:
        self._set_overlay_rectangle(x_start=start, x_end=end)

    def _on_hover(self, sender: Sender, app_data: Any, user_data: Any) -> None:
        super()._on_hover(sender, app_data, user_data)
        GUIStatusBar.set(self._msg_navigation)

    def _set_overlay_rectangle(self, x_start: float = 0.0, x_end: float = 0.0) -> None:
        _min_y = self._layout.graph.min_y
        _max_y = self._layout.graph.max_y

        if not dpg.does_item_exist(self.overlay_rectangle_tag):
            dpg.add_shade_series(
                [x_start, x_end],
                y1=[_min_y, _min_y],
                y2=[_max_y, _max_y],
                tag=self.overlay_rectangle_tag,
                parent=self.y_axis_tag,
            )

            self.overlay_theme.bind_to_item(self.overlay_rectangle_tag)
        else:
            dpg.configure_item(
                self.overlay_rectangle_tag,
                x=[x_start, x_end],
                y1=[_min_y, _min_y],
                y2=[_max_y, _max_y],
            )

    def load_library_fragment(self, fragment: InstructionLibraryFragment[Any]) -> None:
        self.clear_layers()
        self.current_data = fragment
        self.current_position = 0

        self.add_layer(
            InstructionLayer(
                data=fragment,
                name=self._lbl_sample_name,
                color=self._layout.colors.waveform_sample,
                line_thickness=self._layout.waveform.sample_thickness,
            )
        )

        self._update_axes_limits()
        self._update_position_indicator()

    def _extract_reconstruction_layer_data(
        self,
        reconstruction_data: ReconstructionData,
        selected_generators: Optional[List[GeneratorName]] = None,
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        if selected_generators is None:
            selected_generators = list(reconstruction_data.reconstruction.approximations.keys())

        original_audio = reconstruction_data.original_audio
        approximation = reconstruction_data.get_partials(selected_generators)
        full_approximation = reconstruction_data.reconstruction.approximation

        if not self.reconstruction_autoscale:
            return original_audio, approximation, 1.0

        original_audio_coefficient = reconstruction_data.reconstruction.coefficient
        original_audio = original_audio / original_audio_coefficient

        coefficient = max(
            np.max(np.abs(full_approximation)),
            np.max(np.abs(original_audio)),
        )

        return original_audio, approximation, coefficient

    def _extract_layers(
        self,
        reconstruction_data: ReconstructionData,
        selected_generators: Optional[List[GeneratorName]] = None,
    ) -> Tuple[ArrayLayer, ArrayLayer]:
        original_audio, approximation_data, _ = self._extract_reconstruction_layer_data(
            reconstruction_data,
            selected_generators,
        )

        sample_layer = self.sample_layer(original_audio)
        reconstruction_layer = self.reconstruction_layer(approximation_data)
        return sample_layer, reconstruction_layer

    def update_reconstruction_data(
        self,
        reconstruction_data: ReconstructionData,
        selected_generators: Optional[List[GeneratorName]] = None,
    ) -> None:
        if not isinstance(self.current_data, ReconstructionData):
            return

        self.current_data = reconstruction_data
        sample_layer, reconstruction_layer = self._extract_layers(
            reconstruction_data,
            selected_generators,
        )

        self.layers[self._lbl_waveform_reconstruction] = reconstruction_layer
        self.layers[self._lbl_waveform_original] = sample_layer
        self._update_display()

    def load_reconstruction_data(
        self,
        reconstruction_data: ReconstructionData,
        selected_generators: Optional[List[GeneratorName]] = None,
    ) -> None:
        self.clear_layers()
        self.current_data = reconstruction_data
        sample_layer, reconstruction_layer = self._extract_layers(
            reconstruction_data,
            selected_generators,
        )

        self._add_reconstruction_layers(reconstruction_layer, sample_layer)

    def reconstruction_layer(self, data: np.ndarray) -> ArrayLayer:
        return ArrayLayer(
            data=data,
            name=self._lbl_waveform_reconstruction,
            color=self._layout.colors.waveform_reconstruction,
            line_thickness=self._layout.waveform.reconstruction_thickness,
            max_display_points=self._layout.waveform.max_display_points,
        )

    def sample_layer(self, data: np.ndarray) -> ArrayLayer:
        return ArrayLayer(
            data=data,
            name=self._lbl_waveform_original,
            color=self._layout.colors.waveform_sample,
            line_thickness=self._layout.waveform.sample_thickness,
            max_display_points=self._layout.waveform.max_display_points,
        )

    def _add_reconstruction_layers(
        self,
        reconstruction_layer: ArrayLayer,
        sample_layer: ArrayLayer,
    ) -> None:
        self.add_layer(sample_layer)
        self.add_layer(reconstruction_layer)
        self._update_display()

    def clear(self) -> None:
        self.clear_layers()
        dpg_delete_children(self.y_axis_tag)
        self._set_overlay_rectangle()

    def set_autoscale(self, autoscale: bool) -> None:
        self.reconstruction_autoscale = autoscale
        if isinstance(self.current_data, ReconstructionData):
            self.load_reconstruction_data(self.current_data)
            self._update_ranges()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        for layer in self.layers.values():
            series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}".lower()
            theme_tag = f"{series_tag}{SUF_GRAPH_THEME}"
            if dpg.does_item_exist(series_tag):
                dpg.configure_item(
                    series_tag,
                    x=layer.x_data,
                    y=layer.y_data,
                )
            else:
                dpg.add_line_series(
                    layer.x_data.tolist(),
                    layer.y_data.tolist(),
                    label=layer.name,
                    parent=self.y_axis_tag,
                    tag=series_tag,
                )

            if not dpg.does_item_exist(theme_tag):
                with dpg.theme(tag=theme_tag):
                    with dpg.theme_component(dpg.mvLineSeries):
                        dpg.add_theme_color(
                            dpg.mvPlotCol_Line,
                            layer.color,
                            category=dpg.mvThemeCat_Plots,
                        )

            dpg_bind_item_theme(series_tag, theme_tag)

    def _add_position_indicator(self) -> None:
        dpg_delete_item(self.position_indicator_tag)
        dpg.add_inf_line_series(
            [0.0],
            tag=self.position_indicator_tag,
            parent=self.y_axis_tag,
            show=False,
        )
        self.indicator_theme.bind_to_item(self.position_indicator_tag)

    def _update_position_indicator(self) -> None:
        position_x = float(self.current_position)
        show = position_x > 0
        dpg_configure_item(
            self.position_indicator_tag,
            x=[position_x],
            show=show,
        )

    def set_position(self, position: int) -> None:
        self.current_position = position
        self._update_position_indicator()
