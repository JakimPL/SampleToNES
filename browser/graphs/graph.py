from typing import Any, Dict, Tuple

import dearpygui.dearpygui as dpg

from browser.constants import (
    DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
    DIM_GRAPH_DEFAULT_WIDTH,
    LBL_WAVEFORM_DISPLAY,
    SUF_GRAPH_CONTROLS,
    SUF_GRAPH_INFO,
    SUF_GRAPH_LEGEND,
    SUF_GRAPH_PLOT,
    SUF_GRAPH_X_AXIS,
    SUF_GRAPH_Y_AXIS,
    VAL_GRAPH_DEFAULT_X_MAX,
    VAL_WAVEFORM_DEFAULT_X_MIN,
    VAL_WAVEFORM_DEFAULT_Y_MAX,
    VAL_WAVEFORM_DEFAULT_Y_MIN,
)
from browser.panel import GUIPanel


class GUIGraphDisplay(GUIPanel):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_DEFAULT_WIDTH,
        height: int = DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
        label: str = LBL_WAVEFORM_DISPLAY,
    ):
        self.label = label
        self.plot_tag = f"{tag}{SUF_GRAPH_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_GRAPH_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_GRAPH_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_GRAPH_LEGEND}"
        self.controls_tag = f"{tag}{SUF_GRAPH_CONTROLS}"
        self.info_tag = f"{tag}{SUF_GRAPH_INFO}"

        self.x_min: float = VAL_WAVEFORM_DEFAULT_X_MIN
        self.x_max: float = VAL_GRAPH_DEFAULT_X_MAX
        self.y_min: float = VAL_WAVEFORM_DEFAULT_Y_MIN
        self.y_max: float = VAL_WAVEFORM_DEFAULT_Y_MAX
        self.default_y_range = (VAL_WAVEFORM_DEFAULT_Y_MIN, VAL_WAVEFORM_DEFAULT_Y_MAX)

        self.layers: Dict[str, Any] = {}

        super().__init__(
            tag=tag,
            parent_tag=parent,
            width=width,
            height=height,
            init=True,
        )

    def create_panel(self) -> None:
        with dpg.group(tag=self.tag, parent=self.parent_tag):
            self._create_content()

    def _create_content(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def add_layer(self, layer: Any) -> None:
        self.layers[layer.name] = layer
        self._update_display()

    def remove_layer(self, name: str) -> None:
        if name in self.layers:
            del self.layers[name]
            self._update_display()

    def clear_layers(self) -> None:
        self.layers.clear()
        self._update_display()

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
