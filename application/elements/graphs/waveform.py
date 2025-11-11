from typing import Any, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from application.elements.graphs.graph import GUIGraphDisplay
from application.elements.graphs.layers.array import ArrayLayer
from application.elements.graphs.layers.waveform import WaveformLayer
from application.reconstruction.data import ReconstructionData
from constants.browser import (
    CLR_WAVEFORM_LAYER_RECONSTRUCTION,
    CLR_WAVEFORM_LAYER_SAMPLE,
    CLR_WAVEFORM_POSITION_INDICATOR,
    DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
    DIM_GRAPH_DEFAULT_WIDTH,
    LBL_PLOT_ORIGINAL,
    LBL_PLOT_RECONSTRUCTION,
    LBL_WAVEFORM_AMPLITUDE_LABEL,
    LBL_WAVEFORM_BUTTON_RESET_ALL,
    LBL_WAVEFORM_BUTTON_RESET_X,
    LBL_WAVEFORM_BUTTON_RESET_Y,
    LBL_WAVEFORM_DISPLAY,
    LBL_WAVEFORM_SAMPLE_LAYER_NAME,
    LBL_WAVEFORM_TIME_LABEL,
    SUF_WAVEFORM_POSITION_INDICATOR,
    VAL_GRAPH_DEFAULT_X_MAX,
    VAL_GRAPH_DEFAULT_X_MIN,
    VAL_WAVEFORM_AXIS_SLOT,
    VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS,
    VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
    VAL_WAVEFORM_SAMPLE_THICKNESS,
    VAL_WAVEFORM_ZOOM_FACTOR,
)
from constants.enums import GeneratorName
from library.data import LibraryFragment


class GUIWaveformDisplay(GUIGraphDisplay):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_DEFAULT_WIDTH,
        height: int = DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
        label: str = LBL_WAVEFORM_DISPLAY,
        x_min: float = VAL_GRAPH_DEFAULT_X_MIN,
        x_max: float = VAL_GRAPH_DEFAULT_X_MAX,
        y_min: float = -1.0,
        y_max: float = 1.0,
    ):
        self.is_dragging = False
        self.last_mouse_position: Tuple[float, float] = (0.0, 0.0)
        self.zoom_factor = VAL_WAVEFORM_ZOOM_FACTOR
        self.reconstruction_autoscale = True

        self.current_position: int = 0
        self.position_indicator_tag = f"{tag}{SUF_WAVEFORM_POSITION_INDICATOR}"
        self.current_data: Optional[Union[LibraryFragment, ReconstructionData]] = None

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

    @property
    def sample_length(self) -> float:
        if isinstance(self.current_data, LibraryFragment):
            return float(len(self.current_data.sample))
        elif isinstance(self.current_data, ReconstructionData):
            return float(len(self.current_data.reconstruction.approximation))

        return 0.0

    def _get_sample_length_int(self) -> int:
        if isinstance(self.current_data, LibraryFragment):
            return len(self.current_data.sample)
        elif isinstance(self.current_data, ReconstructionData):
            return len(self.current_data.reconstruction.approximation)

        return 0

    def _create_content(self) -> None:
        with dpg.group(tag=self.controls_tag, horizontal=True):
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_X, callback=self._reset_x_axis, small=True)
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_Y, callback=self._reset_y_axis, small=True)
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_ALL, callback=self._reset_all_axes, small=True)

        with dpg.plot(
            label=self.label,
            width=self.width,
            height=self.height,
            tag=self.plot_tag,
            anti_aliased=True,
            callback=self._plot_callback,
            no_inputs=False,
            pan_button=-1,
        ):
            dpg.add_plot_legend(tag=self.legend_tag)
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_WAVEFORM_TIME_LABEL, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_WAVEFORM_AMPLITUDE_LABEL, tag=self.y_axis_tag)

        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self._mouse_wheel_callback)
            dpg.add_mouse_drag_handler(callback=self._mouse_drag_callback)
            dpg.add_mouse_release_handler(callback=self._mouse_release_callback)

    def load_library_fragment(self, fragment: LibraryFragment) -> None:
        self.clear_layers()
        self.current_data = fragment
        self.current_position = 0

        self.add_layer(
            WaveformLayer(
                fragment=fragment,
                name=LBL_WAVEFORM_SAMPLE_LAYER_NAME,
                color=CLR_WAVEFORM_LAYER_SAMPLE,
                line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
            )
        )

        self.x_min = VAL_GRAPH_DEFAULT_X_MIN
        self.x_max = float(len(fragment.sample))
        self._update_axes_limits()
        self._update_position_indicator()

    def load_reconstruction_data(
        self, reconstruction_data: ReconstructionData, selected_generators: Optional[List[GeneratorName]] = None
    ) -> None:
        self.clear_layers()
        self.current_data = reconstruction_data
        self.current_position = 0

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

        self.add_layer(
            ArrayLayer(
                data=original_audio / (coefficient * original_audio_coefficient),
                name=LBL_PLOT_ORIGINAL,
                color=CLR_WAVEFORM_LAYER_SAMPLE,
                line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
            )
        )

        self.add_layer(
            ArrayLayer(
                data=approximation / coefficient,
                name=LBL_PLOT_RECONSTRUCTION,
                color=CLR_WAVEFORM_LAYER_RECONSTRUCTION,
                line_thickness=VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
            )
        )

        self.x_min = 0.0
        self.x_max = float(len(reconstruction_data.original_audio))
        self._update_axes_limits()
        self._update_position_indicator()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        for layer in self.layers.values():
            series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}"
            dpg.add_line_series(
                layer.x_data,
                layer.y_data,
                label=layer.name,
                parent=self.y_axis_tag,
                tag=series_tag,
            )

            with dpg.theme() as series_theme:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, layer.color, category=dpg.mvThemeCat_Plots)

            dpg.bind_item_theme(series_tag, series_theme)

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)

        if dpg.does_item_exist(self.position_indicator_tag):
            position_x = float(self.current_position)
            dpg.configure_item(
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

        if dpg.does_item_exist(self.position_indicator_tag):
            dpg.delete_item(self.position_indicator_tag)

        sample_length = self._get_sample_length_int()
        if self.current_position > 0 and self.current_position < sample_length:
            position_x = float(self.current_position)

            dpg.add_line_series(
                [position_x, position_x],
                [self.y_min, self.y_max],
                parent=self.y_axis_tag,
                tag=self.position_indicator_tag,
            )

            with dpg.theme() as indicator_theme:
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(
                        dpg.mvPlotCol_Line, CLR_WAVEFORM_POSITION_INDICATOR, category=dpg.mvThemeCat_Plots
                    )
                    dpg.add_theme_style(
                        dpg.mvPlotStyleVar_LineWeight,
                        VAL_WAVEFORM_POSITION_INDICATOR_THICKNESS,
                        category=dpg.mvThemeCat_Plots,
                    )

            dpg.bind_item_theme(self.position_indicator_tag, indicator_theme)

    def _reset_x_axis(self) -> None:
        if self.layers:
            max_length = max(len(layer.x_data) for layer in self.layers.values())
            self.x_min = VAL_GRAPH_DEFAULT_X_MIN
            self.x_max = float(max_length)
        else:
            self.x_min = VAL_GRAPH_DEFAULT_X_MIN
            self.x_max = VAL_GRAPH_DEFAULT_X_MAX
        self._update_axes_limits()

    def _reset_y_axis(self) -> None:
        self.y_min, self.y_max = self.default_y_range
        self._update_axes_limits()

    def _reset_all_axes(self) -> None:
        self._reset_x_axis()
        self._reset_y_axis()

    def _plot_callback(self, sender: str, app_data: Any) -> None:
        pass

    def _clamp_zoom_bounds(
        self, new_min: float, new_max: float, bound_min: float, bound_max: float
    ) -> Tuple[float, float]:
        new_range = new_max - new_min
        max_range = bound_max - bound_min

        if new_range > max_range:
            return bound_min, bound_max

        clamped_min = max(bound_min, new_min)
        clamped_max = min(bound_max, new_max)

        if clamped_max - clamped_min < new_range:
            if new_min < bound_min:
                clamped_max = min(bound_max, clamped_min + new_range)
            elif new_max > bound_max:
                clamped_min = max(bound_min, clamped_max - new_range)

        return clamped_min, clamped_max

    def _mouse_wheel_callback(self, sender: str, app_data: float) -> None:
        if not dpg.is_item_hovered(self.plot_tag) or not self.current_data:
            return

        plot_mouse_pos = dpg.get_plot_mouse_pos()
        if not plot_mouse_pos:
            return

        zoom_amount = self.zoom_factor if app_data > 0 else 1.0 / self.zoom_factor
        shift_held = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)

        if shift_held:
            self.y_min, self.y_max = self._zoom_axis(zoom_amount, plot_mouse_pos[1], self.y_min, self.y_max, -1.0, 1.0)
        else:
            self.x_min, self.x_max = self._zoom_axis(
                zoom_amount, plot_mouse_pos[0], self.x_min, self.x_max, 0.0, self.sample_length
            )

        self._update_axes_limits()

    def _zoom_axis(
        self,
        zoom_amount: float,
        center: float,
        current_min: float,
        current_max: float,
        bound_min: float,
        bound_max: float,
    ) -> Tuple[float, float]:
        current_range = current_max - current_min
        new_range = current_range / zoom_amount
        offset = (center - current_min) / current_range if current_range > 0 else 0.5

        new_min = center - new_range * offset
        new_max = center + new_range * (1 - offset)

        return self._clamp_zoom_bounds(new_min, new_max, bound_min, bound_max)

    def _mouse_drag_callback(self, sender: str, app_data: List[Union[int, float]]) -> None:
        if not dpg.is_item_hovered(self.plot_tag) or not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            return

        if not self.current_data:
            return

        x_position = app_data[1]
        y_position = app_data[2]

        if not self.is_dragging:
            self.is_dragging = True
            self.last_mouse_position = x_position, y_position
            return

        dx_screen = x_position - self.last_mouse_position[0]
        dy_screen = y_position - self.last_mouse_position[1]

        plot_bounds = dpg.get_item_rect_size(self.plot_tag)
        if plot_bounds:
            x_range = self.x_max - self.x_min
            y_range = self.y_max - self.y_min

            dx_plot = -(dx_screen / plot_bounds[0]) * x_range
            dy_plot = (dy_screen / plot_bounds[1]) * y_range

            dx_plot = np.clip(dx_plot, -self.x_min, self.sample_length - self.x_max)
            dy_plot = np.clip(dy_plot, -1.0 - self.y_min, 1.0 - self.y_max)

            new_x_min = self.x_min + dx_plot
            new_x_max = self.x_max + dx_plot
            new_y_min = self.y_min + dy_plot
            new_y_max = self.y_max + dy_plot

            self.set_view_bounds(new_x_min, new_x_max, new_y_min, new_y_max)
            self.last_mouse_position = x_position, y_position

    def _mouse_release_callback(self, sender: str, app_data: int) -> None:
        if app_data == dpg.mvMouseButton_Left:
            self.is_dragging = False
