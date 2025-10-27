from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from browser.constants import (
    CLR_WAVEFORM_LAYER_RECONSTRUCTION,
    CLR_WAVEFORM_LAYER_SAMPLE,
    DIM_WAVEFORM_DEFAULT_DISPLAY_HEIGHT,
    DIM_WAVEFORM_DEFAULT_WIDTH,
    LBL_WAVEFORM_AMPLITUDE_LABEL,
    LBL_WAVEFORM_BUTTON_RESET_ALL,
    LBL_WAVEFORM_BUTTON_RESET_X,
    LBL_WAVEFORM_BUTTON_RESET_Y,
    LBL_WAVEFORM_RECONSTRUCTION_LAYER_NAME,
    LBL_WAVEFORM_SAMPLE_LAYER_NAME,
    LBL_WAVEFORM_TIME_LABEL,
    MSG_WAVEFORM_NO_FRAGMENT,
    SUF_WAVEFORM_CONTROLS,
    SUF_WAVEFORM_INFO,
    SUF_WAVEFORM_LEGEND,
    SUF_WAVEFORM_PLOT,
    SUF_WAVEFORM_X_AXIS,
    SUF_WAVEFORM_Y_AXIS,
    VAL_WAVEFORM_AXIS_SLOT,
    VAL_WAVEFORM_DEFAULT_X_MAX,
    VAL_WAVEFORM_DEFAULT_X_MIN,
    VAL_WAVEFORM_DEFAULT_Y_MAX,
    VAL_WAVEFORM_DEFAULT_Y_MIN,
    VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
    VAL_WAVEFORM_SAMPLE_THICKNESS,
    VAL_WAVEFORM_ZOOM_FACTOR,
)
from browser.waveform.layer import WaveformLayer
from library.data import LibraryFragment


class WaveformDisplay:
    def __init__(
        self,
        tag: str,
        width: int = DIM_WAVEFORM_DEFAULT_WIDTH,
        height: int = DIM_WAVEFORM_DEFAULT_DISPLAY_HEIGHT,
        parent: Optional[str] = None,
        label: str = "Waveform Display",
    ):
        self.tag = tag
        self.width = width
        self.height = height
        self.parent = parent
        self.label = label

        self.plot_tag = f"{tag}{SUF_WAVEFORM_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_WAVEFORM_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_WAVEFORM_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_WAVEFORM_LEGEND}"
        self.controls_tag = f"{tag}{SUF_WAVEFORM_CONTROLS}"
        self.info_tag = f"{tag}{SUF_WAVEFORM_INFO}"

        self.layers: Dict[str, WaveformLayer] = {}
        self.current_library_fragment: Optional[LibraryFragment] = None

        self.x_min: float = VAL_WAVEFORM_DEFAULT_X_MIN
        self.x_max: float = VAL_WAVEFORM_DEFAULT_X_MAX
        self.y_min: float = VAL_WAVEFORM_DEFAULT_Y_MIN
        self.y_max: float = VAL_WAVEFORM_DEFAULT_Y_MAX
        self.default_y_range = (VAL_WAVEFORM_DEFAULT_Y_MIN, VAL_WAVEFORM_DEFAULT_Y_MAX)

        self.is_dragging = False
        self.last_mouse_position: Tuple[float, float] = (0.0, 0.0)
        self.zoom_factor = VAL_WAVEFORM_ZOOM_FACTOR

        self._create_display()
        self._update_axes_limits()

    @property
    def sample_length(self) -> float:
        if self.current_library_fragment:
            return float(len(self.current_library_fragment.sample))
        return VAL_WAVEFORM_DEFAULT_X_MAX

    def _create_display(self) -> None:
        if self.parent:
            with dpg.group(tag=self.tag, parent=self.parent):
                self._create_waveform_content()
        else:
            with dpg.group(tag=self.tag):
                self._create_waveform_content()

    def _create_waveform_content(self) -> None:
        with dpg.group(tag=self.controls_tag, horizontal=True):
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_X, callback=self._reset_x_axis, small=True)
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_Y, callback=self._reset_y_axis, small=True)
            dpg.add_button(label=LBL_WAVEFORM_BUTTON_RESET_ALL, callback=self._reset_all_axes, small=True)

        dpg.add_text(MSG_WAVEFORM_NO_FRAGMENT, tag=self.info_tag)

        with dpg.plot(
            label=self.label,
            height=self.height,
            width=self.width,
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

    def add_layer(
        self,
        name: str,
        data: np.ndarray,
        color: Tuple[int, int, int, int] = (255, 255, 255, 255),
        visible: bool = True,
        line_thickness: float = 1.0,
    ) -> None:
        layer = WaveformLayer(name=name, data=data, color=color, visible=visible, line_thickness=line_thickness)
        self.layers[name] = layer
        self._update_display()

    def remove_layer(self, name: str) -> None:
        if name in self.layers:
            del self.layers[name]
            self._update_display()

    def clear_layers(self) -> None:
        self.layers.clear()
        self._update_display()

    def load_library_fragment(self, fragment: LibraryFragment) -> None:
        self.current_library_fragment = fragment
        self.clear_layers()

        self.add_layer(
            LBL_WAVEFORM_SAMPLE_LAYER_NAME,
            fragment.sample,
            color=CLR_WAVEFORM_LAYER_SAMPLE,
            line_thickness=VAL_WAVEFORM_SAMPLE_THICKNESS,
        )

        self._update_info_display()

        self.x_min = VAL_WAVEFORM_DEFAULT_X_MIN
        self.x_max = float(len(fragment.sample))
        self._update_axes_limits()

    def add_reconstruction_comparison(self, reconstruction: np.ndarray) -> None:
        if len(reconstruction) > 0:
            self.add_layer(
                LBL_WAVEFORM_RECONSTRUCTION_LAYER_NAME,
                reconstruction,
                color=CLR_WAVEFORM_LAYER_RECONSTRUCTION,
                line_thickness=VAL_WAVEFORM_RECONSTRUCTION_THICKNESS,
            )

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_WAVEFORM_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        for layer in self.layers.values():
            if layer.visible and len(layer.data) > 0:
                x_data = [float(i) for i in range(len(layer.data))]
                y_data = layer.data.tolist()

                series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}"
                dpg.add_line_series(x_data, y_data, label=layer.name, parent=self.y_axis_tag, tag=series_tag)

                with dpg.theme() as series_theme:
                    with dpg.theme_component(dpg.mvLineSeries):
                        dpg.add_theme_color(dpg.mvPlotCol_Line, layer.color, category=dpg.mvThemeCat_Plots)
                dpg.bind_item_theme(series_tag, series_theme)

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)

    def _update_info_display(self) -> None:
        if not dpg.does_item_exist(self.info_tag):
            return

        if not self.current_library_fragment:
            dpg.set_value(self.info_tag, MSG_WAVEFORM_NO_FRAGMENT)
            return

        dpg.set_value(self.info_tag, "")

    def _reset_x_axis(self) -> None:
        if self.layers:
            max_length = max(len(layer.data) for layer in self.layers.values())
            self.x_min = VAL_WAVEFORM_DEFAULT_X_MIN
            self.x_max = float(max_length)
        else:
            self.x_min = VAL_WAVEFORM_DEFAULT_X_MIN
            self.x_max = VAL_WAVEFORM_DEFAULT_X_MAX
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
        if not dpg.is_item_hovered(self.plot_tag) or not self.current_library_fragment:
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

        if not self.current_library_fragment:
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

    def set_view_bounds(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self._update_axes_limits()

    def get_view_bounds(self) -> Tuple[float, float, float, float]:
        return self.x_min, self.x_max, self.y_min, self.y_max

    def export_view_as_image(self, path: Union[str, Path]) -> None:
        pass
