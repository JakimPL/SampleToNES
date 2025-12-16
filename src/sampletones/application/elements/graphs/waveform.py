from typing import Any, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.constants.enums import GeneratorName
from sampletones.library import InstructionLibraryFragment

from ...constants.graphs import (
    COL_WAVEFORM_LAYER_RECONSTRUCTION,
    COL_WAVEFORM_LAYER_SAMPLE,
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_BUTTON_WAVEFORM_RESET_ALL,
    LBL_BUTTON_WAVEFORM_RESET_X,
    LBL_BUTTON_WAVEFORM_RESET_Y,
    LBL_GRAPH_WAVEFORM_ORIGINAL,
    LBL_GRAPH_WAVEFORM_RECONSTRUCTION,
    LBL_PLOT_AXIS_WAVEFORM_AMPLITUDE,
    LBL_PLOT_AXIS_WAVEFORM_TIME,
    LBL_PLOT_LABEL_WAVEFORM,
    LBL_PLOT_NAME_WAVEFORM_SAMPLE,
    SUF_BUTTON_WAVEFORM_RESET_ALL,
    SUF_BUTTON_WAVEFORM_RESET_X,
    SUF_BUTTON_WAVEFORM_RESET_Y,
    SUF_GRAPH_THEME,
    SUF_WAVEFORM_OVERLAY,
    SUF_WAVEFORM_POSITION_INDICATOR,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MAX_GRAPH_DEFAULT_Y,
    VAL_MIN_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_Y,
    VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
    VAL_WAVEFORM_SAMPLE_THICKNESS,
)
from ...elements.fonts.font import Font
from ...reconstruction.data import ReconstructionData
from ...themes.graphs.indicator import IndicatorGraphTheme
from ...themes.graphs.overlay import OverlayGraphTheme
from ...utils.align import table_wrapper
from ...utils.dpg import (
    dpg_bind_item_theme,
    dpg_configure_item,
    dpg_delete_children,
    dpg_delete_item,
)
from ...utils.thread import concurrent
from ..button import GUIButton
from .graph import GUIGraph
from .layers.array import ArrayLayer
from .layers.waveform import WaveformLayer


class GUIWaveformGraph(GUIGraph):
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
        label: str = LBL_PLOT_LABEL_WAVEFORM,
        x_min: float = VAL_MIN_GRAPH_DEFAULT_X,
        x_max: float = VAL_MAX_GRAPH_DEFAULT_X,
        y_min: float = VAL_MIN_GRAPH_DEFAULT_Y,
        y_max: float = VAL_MAX_GRAPH_DEFAULT_Y,
        default_x_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_X, VAL_MAX_GRAPH_DEFAULT_X),
        default_y_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_Y, VAL_MAX_GRAPH_DEFAULT_Y),
        enable_dragging: bool = True,
    ):
        self.reconstruction_autoscale = True

        self.reset_x_tag = f"{tag}{SUF_BUTTON_WAVEFORM_RESET_X}"
        self.reset_y_tag = f"{tag}{SUF_BUTTON_WAVEFORM_RESET_Y}"
        self.reset_all_tag = f"{tag}{SUF_BUTTON_WAVEFORM_RESET_ALL}"

        self.position_indicator_tag = f"{tag}{SUF_WAVEFORM_POSITION_INDICATOR}"
        self.overlay_rectangle_tag = f"{tag}{SUF_WAVEFORM_OVERLAY}"

        self.indicator_theme = IndicatorGraphTheme()
        self.overlay_theme = OverlayGraphTheme()

        self.current_data: Optional[Union[InstructionLibraryFragment[Any], ReconstructionData]] = None
        self.current_position: int = 0

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
            default_x_range=default_x_range,
            default_y_range=default_y_range,
            enable_dragging=enable_dragging,
        )

    def delete(self) -> None:
        dpg_delete_item(self.position_indicator_tag)
        dpg_delete_item(self.overlay_rectangle_tag)
        super().delete()

    @property
    def sample_length(self) -> int:
        if isinstance(self.current_data, InstructionLibraryFragment):
            return len(self.current_data.data)

        if isinstance(self.current_data, ReconstructionData):
            return len(self.current_data.reconstruction.approximation)

        return 0

    def _create_content(self) -> None:
        with dpg.group(
            tag=self.controls_tag,
            parent=self.tag,
            horizontal=True,
        ):
            self._create_controls()

        with dpg.plot(
            label=self.label,
            tag=self.plot_tag,
            parent=self.tag,
            width=self.width,
            height=self.height,
            anti_aliased=True,
            no_inputs=False,
            pan_button=-1,
        ):
            dpg.add_plot_legend(tag=self.legend_tag, parent=self.plot_tag, location=dpg.mvPlot_Location_NorthEast)
            dpg.add_plot_axis(dpg.mvXAxis, parent=self.plot_tag, label=LBL_PLOT_AXIS_WAVEFORM_TIME, tag=self.x_axis_tag)
            dpg.add_plot_axis(
                dpg.mvYAxis,
                parent=self.plot_tag,
                label=LBL_PLOT_AXIS_WAVEFORM_AMPLITUDE,
                tag=self.y_axis_tag,
            )
            self._set_overlay_rectangle()

    @table_wrapper(columns=3, height=0)
    def _create_controls(self) -> None:
        GUIButton(
            tag=self.reset_x_tag,
            label=LBL_BUTTON_WAVEFORM_RESET_X,
            callback=self._reset_x_axis,
            width=-1,
            font=Font.REGULAR_SMALL,
        )
        GUIButton(
            tag=self.reset_y_tag,
            label=LBL_BUTTON_WAVEFORM_RESET_Y,
            callback=self._reset_y_axis,
            width=-1,
            font=Font.REGULAR_SMALL,
        )
        GUIButton(
            tag=self.reset_all_tag,
            label=LBL_BUTTON_WAVEFORM_RESET_ALL,
            callback=self._reset_all_axes,
            width=-1,
            font=Font.REGULAR_SMALL,
        )

    def set_overlay_range(self, start: float = 0.0, end: float = 0.0) -> None:
        self._set_overlay_rectangle(x_start=start, x_end=end)

    def _set_overlay_rectangle(self, x_start: float = 0.0, x_end: float = 0.0) -> None:
        if not dpg.does_item_exist(self.overlay_rectangle_tag):
            dpg.add_shade_series(
                [x_start, x_end],
                [self.y_min, self.y_min],
                y2=[self.y_max, self.y_max],
                tag=self.overlay_rectangle_tag,
                parent=self.y_axis_tag,
            )

            self.overlay_theme.bind_to_item(self.overlay_rectangle_tag)
        else:
            dpg.configure_item(
                self.overlay_rectangle_tag,
                x=[x_start, x_end],
                y1=[self.y_min, self.y_min],
                y2=[self.y_max, self.y_max],
            )

    @concurrent(wait=True, method_bound=True)
    def load_library_fragment(self, fragment: InstructionLibraryFragment[Any]) -> None:
        self.clear_layers()
        self.current_data = fragment
        self.current_position = 0

        self.add_layer(
            WaveformLayer(
                data=fragment,
                name=LBL_PLOT_NAME_WAVEFORM_SAMPLE,
                color=COL_WAVEFORM_LAYER_SAMPLE,
                line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
            )
        )

        self.x_min = VAL_MIN_GRAPH_DEFAULT_X
        self.x_max = float(len(fragment.data))
        self._update_axes_limits()
        self._update_position_indicator()

    def _extract_reconstruction_layer_data(
        self, reconstruction_data: ReconstructionData, selected_generators: Optional[List[GeneratorName]] = None
    ) -> Tuple[np.ndarray, float]:
        if selected_generators is None:
            selected_generators = list(reconstruction_data.reconstruction.approximations.keys())

        approximation = reconstruction_data.get_partials(selected_generators)
        full_approximation = reconstruction_data.reconstruction.approximation
        original_audio = reconstruction_data.original_audio

        original_audio_coefficient = 1.0
        if self.reconstruction_autoscale:
            original_audio_coefficient = reconstruction_data.reconstruction.coefficient

        coefficient = max(
            np.max(np.abs(full_approximation)),
            np.max(np.abs(original_audio / original_audio_coefficient)),
        )

        return approximation / coefficient, coefficient

    @concurrent(wait=True, method_bound=True)
    def update_reconstruction_data(
        self, reconstruction_data: ReconstructionData, selected_generators: Optional[List[GeneratorName]] = None
    ) -> None:
        if not isinstance(self.current_data, ReconstructionData):
            return

        self.current_data = reconstruction_data
        approximation_data, _ = self._extract_reconstruction_layer_data(
            reconstruction_data,
            selected_generators,
        )

        reconstruction_layer = ArrayLayer(
            data=approximation_data,
            name=LBL_GRAPH_WAVEFORM_RECONSTRUCTION,
            color=COL_WAVEFORM_LAYER_RECONSTRUCTION,
            line_thickness=VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
        )

        self.layers[LBL_GRAPH_WAVEFORM_RECONSTRUCTION] = reconstruction_layer
        self._update_display()

    @concurrent(wait=True, method_bound=True)
    def load_reconstruction_data(
        self, reconstruction_data: ReconstructionData, selected_generators: Optional[List[GeneratorName]] = None
    ) -> None:
        self.clear_layers()
        self.current_data = reconstruction_data
        self.current_position = 0

        approximation_data, coefficient = self._extract_reconstruction_layer_data(
            reconstruction_data,
            selected_generators,
        )

        original_audio = reconstruction_data.original_audio
        original_audio_coefficient = 1.0
        if self.reconstruction_autoscale:
            original_audio_coefficient = reconstruction_data.reconstruction.coefficient

        self.add_layer(
            ArrayLayer(
                data=original_audio / (coefficient * original_audio_coefficient),
                name=LBL_GRAPH_WAVEFORM_ORIGINAL,
                color=COL_WAVEFORM_LAYER_SAMPLE,
                line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
            )
        )

        self.add_layer(
            ArrayLayer(
                data=approximation_data,
                name=LBL_GRAPH_WAVEFORM_RECONSTRUCTION,
                color=COL_WAVEFORM_LAYER_RECONSTRUCTION,
                line_thickness=VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
            )
        )

        self.x_min = 0.0
        self.x_max = float(len(reconstruction_data.original_audio))
        self._update_axes_limits()
        self._update_position_indicator()

    def clear(self) -> None:
        self.clear_layers()
        dpg_delete_children(self.y_axis_tag)
        self._set_overlay_rectangle()

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
                    layer.x_data,
                    layer.y_data,
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

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)

        position_x = float(self.current_position)
        dpg_configure_item(
            self.position_indicator_tag,
            x=[position_x, position_x],
            y=[self.y_min, self.y_max],
        )

    def set_position(self, position: int) -> None:
        self.current_position = position
        self._update_position_indicator()

    def _update_position_indicator(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_item(self.position_indicator_tag)
        sample_length = self.sample_length
        if self.current_position > 0 and self.current_position < sample_length:
            position_x = float(self.current_position)

            dpg.add_line_series(
                [position_x, position_x],
                [self.y_min, self.y_max],
                tag=self.position_indicator_tag,
                parent=self.y_axis_tag,
            )
            self.indicator_theme.bind_to_item(self.position_indicator_tag)

    def _reset_x_axis(self) -> None:
        if self.layers:
            max_length = max(len(layer.x_data) for layer in self.layers.values())
            self.x_min = VAL_MIN_GRAPH_DEFAULT_X
            self.x_max = float(max_length)
        else:
            self.x_min = VAL_MIN_GRAPH_DEFAULT_X
            self.x_max = VAL_MAX_GRAPH_DEFAULT_X
        self._update_axes_limits()

    def _reset_y_axis(self) -> None:
        self.y_min, self.y_max = self.default_y_range
        self._update_axes_limits()

    def _reset_all_axes(self) -> None:
        self._reset_x_axis()
        self._reset_y_axis()
