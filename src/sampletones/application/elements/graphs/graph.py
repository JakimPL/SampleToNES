from typing import Any, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.typehints import Sender, SerializedData

from ...constants.graphs import (
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_PLOT_LABEL_WAVEFORM,
    SUF_GRAPH_CONTROLS,
    SUF_GRAPH_INFO,
    SUF_GRAPH_LEGEND,
    SUF_GRAPH_PLOT,
    SUF_GRAPH_X_AXIS,
    SUF_GRAPH_Y_AXIS,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MAX_GRAPH_DEFAULT_Y,
    VAL_MIN_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_Y,
    VAL_WAVEFORM_ZOOM_FACTOR,
)
from ..panel import GUIPanel
from .layers.layer import Layer


class GUIGraph(GUIPanel):
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
        self.label = label
        self.plot_tag = f"{tag}{SUF_GRAPH_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_GRAPH_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_GRAPH_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_GRAPH_LEGEND}"
        self.controls_tag = f"{tag}{SUF_GRAPH_CONTROLS}"
        self.info_tag = f"{tag}{SUF_GRAPH_INFO}"

        self.x_min: float = x_min
        self.x_max: float = x_max
        self.y_min: float = y_min
        self.y_max: float = y_max
        self.default_y_range = (y_min, y_max)

        self.is_dragging = False
        self.enable_dragging = enable_dragging
        self.last_mouse_position: Tuple[float, float] = (0.0, 0.0)
        self.zoom_factor = VAL_WAVEFORM_ZOOM_FACTOR
        self.x_range: Optional[Tuple[float, float]] = None
        self.y_range: Optional[Tuple[float, float]] = None
        self._default_x_range = default_x_range
        self._default_y_range = default_y_range

        self._handlers: List[Sender] = []
        self.layers: SerializedData = {}
        self.current_data: Optional[Any] = None

        super().__init__(
            tag=tag,
            parent=parent,
            width=width,
            height=height,
            init=True,
        )

    def delete(self) -> None:
        for handler in self._handlers:
            dpg.delete_item(handler)

        dpg.delete_item(self.plot_tag)

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag, parent=self.parent):
            self._create_content()

        self._update_axes_limits()
        self._setup_mouse_events()

    def _create_content(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _setup_mouse_events(self) -> None:
        with dpg.handler_registry() as mouse_handler:
            dpg.add_mouse_wheel_handler(callback=self._mouse_wheel_callback)
            dpg.add_mouse_drag_handler(callback=self._mouse_drag_callback)
            dpg.add_mouse_release_handler(callback=self._mouse_release_callback)

        self._handlers.append(mouse_handler)

    def add_layer(self, layer: Layer) -> None:
        self.layers[layer.name] = layer
        self._update_ranges(layer)
        self._update_display()

    def get_x_range(self) -> Tuple[float, float]:
        return self.x_range if self.x_range is not None else self._default_x_range

    def get_y_range(self) -> Tuple[float, float]:
        return self.y_range if self.y_range is not None else self._default_y_range

    def clear_layers(self) -> None:
        self.current_data = None
        self.x_range = None
        self.y_range = None
        self.layers.clear()
        self._update_display()

    def _update_ranges(self, layer: Layer) -> None:
        x_data_min = layer.x_data.min() if len(layer.x_data) > 0 else VAL_MIN_GRAPH_DEFAULT_X
        x_data_max = layer.x_data.max() if len(layer.x_data) > 0 else VAL_MAX_GRAPH_DEFAULT_X
        y_data_min = layer.y_data.min() if len(layer.y_data) > 0 else VAL_MIN_GRAPH_DEFAULT_Y
        y_data_max = layer.y_data.max() if len(layer.y_data) > 0 else VAL_MAX_GRAPH_DEFAULT_Y
        if self.x_range is None or self.y_range is None:
            self.x_range = (x_data_min, x_data_max)
            self.y_range = (y_data_min, y_data_max)
        else:
            self.x_range = (
                min(self.x_range[0], x_data_min),
                max(self.x_range[1], x_data_max),
            )
            self.y_range = (
                min(self.y_range[0], y_data_min),
                max(self.y_range[1], y_data_max),
            )

    def _update_display(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _update_axes_limits(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def set_view_bounds(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self._update_axes_limits()

    def get_view_bounds(self) -> Tuple[float, float, float, float]:
        return self.x_min, self.x_max, self.y_min, self.y_max

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

    def _mouse_wheel_callback(self, sender: Sender, app_data: float) -> None:
        if self.current_data is None:
            return

        if not dpg.is_item_hovered(self.plot_tag):
            return

        plot_mouse_pos = dpg.get_plot_mouse_pos()
        if not plot_mouse_pos:
            return

        zoom_amount = self.zoom_factor if app_data > 0 else 1.0 / self.zoom_factor
        shift_held = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)

        if shift_held:
            self.y_min, self.y_max = self._zoom_axis(
                zoom_amount,
                plot_mouse_pos[1],
                self.y_min,
                self.y_max,
                *self.get_y_range(),
            )
        else:
            self.x_min, self.x_max = self._zoom_axis(
                zoom_amount,
                plot_mouse_pos[0],
                self.x_min,
                self.x_max,
                *self.get_x_range(),
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

    def _mouse_drag_callback(self, sender: Sender, app_data: List[Union[int, float]]) -> None:
        if not dpg.is_item_hovered(self.plot_tag) or not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            return

        if self.current_data is None or not self.enable_dragging:
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

            x_range = self.get_x_range()
            y_range = self.get_y_range()
            dx_plot = np.clip(dx_plot, x_range[0] - self.x_min, x_range[1] - self.x_max)
            dy_plot = np.clip(dy_plot, y_range[0] - self.y_min, y_range[1] - self.y_max)

            new_x_min = self.x_min + dx_plot
            new_x_max = self.x_max + dx_plot
            new_y_min = self.y_min + dy_plot
            new_y_max = self.y_max + dy_plot

            self.set_view_bounds(new_x_min, new_x_max, new_y_min, new_y_max)
            self.last_mouse_position = x_position, y_position

    def _mouse_release_callback(self, sender: Sender, app_data: int) -> None:
        if app_data == dpg.mvMouseButton_Left:
            self.is_dragging = False
