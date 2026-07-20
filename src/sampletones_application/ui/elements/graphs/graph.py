from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.tags.graphs import (
    SUF_GRAPH_CONTROLS,
    SUF_GRAPH_INFO,
    SUF_GRAPH_LEGEND,
    SUF_GRAPH_PLOT,
    SUF_GRAPH_X_AXIS,
    SUF_GRAPH_Y_AXIS,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.graphs.layers.type import LayerT
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_shared.types.application import Sender


class GUIGraph(GUIPanel, ABC, Generic[LayerT]):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int,
        height: int,
        label: str,
        x_range: Tuple[float, float],
        y_range: Tuple[float, float],
        zoom_factor: float,
    ):
        self.label = label
        self.plot_tag = f"{tag}{SUF_GRAPH_PLOT}"
        self.x_axis_tag = f"{tag}{SUF_GRAPH_X_AXIS}"
        self.y_axis_tag = f"{tag}{SUF_GRAPH_Y_AXIS}"
        self.legend_tag = f"{tag}{SUF_GRAPH_LEGEND}"
        self.controls_tag = f"{tag}{SUF_GRAPH_CONTROLS}"
        self.info_tag = f"{tag}{SUF_GRAPH_INFO}"
        self.event_handler_tag = f"{tag}{SUF_HANDLER_REGISTRY}"

        self.zoom_factor = zoom_factor
        self._x_range: Tuple[float, float] = x_range
        self._y_range: Tuple[float, float] = y_range
        self._default_x_range = self._x_range
        self._default_y_range = self._y_range

        self._handlers: List[Sender] = []
        self.layers: Dict[str, LayerT] = {}
        self.current_data: Optional[Any] = None

        super().__init__(
            tag=tag,
            width=width,
            height=height,
        )
        self.create_panel(parent)

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with dpg.group(tag=self.tag, parent=parent):
            self._create_content()

        FontRegistry.bind_to_item(self.plot_tag, Font.MONO_SMALL)
        self._update_axes_limits()

    def set_height(self, height: int) -> None:
        """Resizes the plot to ``height`` so a viewport-driven caller can grow the graph vertically."""
        self.height = height
        dpg_configure_item(self.plot_tag, height=height)

    def _setup_handlers(self) -> None:
        with dpg.item_handler_registry(tag=self.event_handler_tag):
            dpg.add_item_hover_handler(callback=self._on_hover)

    def _bind_event_handler(self) -> None:
        dpg.bind_item_handler_registry(self.plot_tag, self.event_handler_tag)

    @abstractmethod
    def _create_content(self) -> None: ...

    def _on_hover(self, sender: Sender, app_data: int, user_data: Any) -> None:
        shift = dpg.is_key_down(dpg.mvKey_LShift)
        dpg.configure_item(self.x_axis_tag, lock_min=shift, lock_max=shift)
        dpg.configure_item(self.y_axis_tag, lock_min=not shift, lock_max=not shift)
        self._release_axes_limits()

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
            x_min = float(
                min(
                    min(layer.x_data.min() for layer in layers),
                    self._default_x_range[0],
                )
            )
            x_max = float(
                max(
                    max(layer.x_data.max() for layer in layers),
                    self._default_x_range[1],
                )
            )
            y_min = float(
                min(
                    min(layer.y_data.min() for layer in layers),
                    self._default_y_range[0],
                )
            )
            y_max = float(
                max(
                    max(layer.y_data.max() for layer in layers),
                    self._default_y_range[1],
                )
            )
            self.x_range = x_min, x_max
            self.y_range = y_min, y_max

        else:
            self.x_range = self._default_x_range
            self.y_range = self._default_y_range

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, *self.x_range)
        dpg.set_axis_limits_constraints(self.x_axis_tag, *self.x_range)
        dpg.set_axis_limits(self.y_axis_tag, *self.y_range)
        dpg.set_axis_limits_constraints(self.y_axis_tag, *self.y_range)

    def _release_axes_limits(self) -> None:
        dpg.split_frame()
        dpg.set_axis_limits_auto(self.x_axis_tag)
        dpg.set_axis_limits_auto(self.y_axis_tag)

    @abstractmethod
    def _update_display(self) -> None: ...

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
