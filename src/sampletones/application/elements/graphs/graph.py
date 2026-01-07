from typing import Any, Dict, Generic, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.typehints import Sender

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
from .layers.type import LayerT


class GUIGraph(GUIPanel, Generic[LayerT]):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_WIDTH,
        height: int = DIM_GRAPH_HEIGHT,
        label: str = LBL_PLOT_LABEL_WAVEFORM,
        x_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_X, VAL_MAX_GRAPH_DEFAULT_X),
        y_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_Y, VAL_MAX_GRAPH_DEFAULT_Y),
    ):
        self.label = label
        self.plot_tag = f"{tag}{SUF_GRAPH_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_GRAPH_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_GRAPH_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_GRAPH_LEGEND}"
        self.controls_tag = f"{tag}{SUF_GRAPH_CONTROLS}"
        self.info_tag = f"{tag}{SUF_GRAPH_INFO}"

        self.zoom_factor = VAL_WAVEFORM_ZOOM_FACTOR
        self._x_range: Tuple[float, float] = x_range
        self._y_range: Tuple[float, float] = y_range
        self._default_x_range = self._x_range
        self._default_y_range = self._y_range

        self._handlers: List[Sender] = []
        self.layers: Dict[str, LayerT] = {}
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

    def _create_content(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def add_layer(self, layer: LayerT) -> None:
        self.layers[layer.name] = layer
        self._update_ranges()
        self._update_display()

    def clear_layers(self) -> None:
        self.current_data = None
        self.x_range = None
        self.y_range = None
        self.layers.clear()
        self._update_display()

    def _update_ranges(self) -> None:
        layers = [layer for layer in self.layers.values() if layer.x_data.size > 0 and layer.y_data.size > 0]
        if layers:
            x_min = min(layer.x_data.min() for layer in layers)
            x_max = max(layer.x_data.max() for layer in layers)
            y_min = min(min(layer.y_data.min() for layer in layers), VAL_MIN_GRAPH_DEFAULT_Y)
            y_max = max(max(layer.y_data.max() for layer in layers), VAL_MAX_GRAPH_DEFAULT_Y)
            self.x_range = x_min, x_max
            self.y_range = y_min, y_max

        else:
            self.x_range = self._default_x_range
            self.y_range = self._default_y_range

        self._update_axes_limits()

    def _update_display(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _update_axes_limits(self, x: bool = True, y: bool = True) -> None:
        if x:
            dpg.set_axis_limits_constraints(self.x_axis_tag, *self.x_range)
        if y:
            dpg.set_axis_limits_constraints(self.y_axis_tag, *self.y_range)

        dpg.fit_axis_data(self.x_axis_tag)
        dpg.fit_axis_data(self.y_axis_tag)

    @property
    def x_range(self) -> Tuple[float, float]:
        return self._x_range

    @x_range.setter
    def x_range(self, value: Optional[Tuple[float, float]]) -> None:
        if value is None:
            self._x_range = self._default_x_range
        else:
            self._x_range = value

    @property
    def y_range(self) -> Tuple[float, float]:
        return self._y_range

    @y_range.setter
    def y_range(self, value: Optional[Tuple[float, float]]) -> None:
        if value is None:
            self._y_range = self._default_y_range
        else:
            self._y_range = value
