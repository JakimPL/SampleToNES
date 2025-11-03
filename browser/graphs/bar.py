from typing import Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from browser.graphs.graph import GUIGraphDisplay
from browser.graphs.layers.bar import BarLayer
from constants.browser import (
    DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
    DIM_GRAPH_DEFAULT_WIDTH,
    LBL_BAR_PLOT_DISPLAY,
    LBL_BAR_PLOT_FRAME_LABEL,
    LBL_BAR_PLOT_VALUE_LABEL,
    MSG_BAR_PLOT_NO_DATA,
    VAL_BAR_PLOT_AXIS_SLOT,
    VAL_BAR_PLOT_DEFAULT_X_MIN,
    VAL_BAR_PLOT_DEFAULT_Y_MAX,
    VAL_BAR_PLOT_DEFAULT_Y_MIN,
    VAL_GRAPH_DEFAULT_X_MAX,
    VAL_GRAPH_DEFAULT_X_MIN,
)


class GUIBarPlotDisplay(GUIGraphDisplay):
    def __init__(
        self,
        tag: str,
        parent: str,
        width: int = DIM_GRAPH_DEFAULT_WIDTH,
        height: int = DIM_GRAPH_DEFAULT_DISPLAY_HEIGHT,
        label: str = LBL_BAR_PLOT_DISPLAY,
        x_min: float = VAL_GRAPH_DEFAULT_X_MIN,
        x_max: float = VAL_GRAPH_DEFAULT_X_MAX,
        y_min: float = VAL_BAR_PLOT_DEFAULT_Y_MIN,
        y_max: float = VAL_BAR_PLOT_DEFAULT_Y_MAX,
    ):
        super().__init__(tag, parent, width, height, label, x_min, x_max, y_min, y_max)
        self.current_data: Optional[np.ndarray] = None

    def _create_content(self) -> None:
        with dpg.plot(
            label=self.label,
            height=self.height,
            width=self.width,
            tag=self.plot_tag,
            anti_aliased=True,
        ):
            dpg.add_plot_legend(tag=self.legend_tag)
            dpg.add_plot_axis(dpg.mvXAxis, label=LBL_BAR_PLOT_FRAME_LABEL, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, label=LBL_BAR_PLOT_VALUE_LABEL, tag=self.y_axis_tag)

    def load_data(self, data: np.ndarray, name: str, color: Tuple[int, int, int, int]) -> None:
        self.clear_layers()
        self.current_data = data

        self.add_layer(BarLayer(data=data, name=name, color=color))

        self.x_min = VAL_BAR_PLOT_DEFAULT_X_MIN
        self.x_max = float(len(data))

        self._update_axes_limits()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        children = dpg.get_item_children(self.y_axis_tag, slot=VAL_BAR_PLOT_AXIS_SLOT) or []
        for child in children:
            dpg.delete_item(child)

        for layer in self.layers.values():
            series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}"
            dpg.add_bar_series(
                layer.x_data,
                layer.y_data,
                label=layer.name,
                parent=self.y_axis_tag,
                tag=series_tag,
                weight=layer.bar_weight,
            )

            with dpg.theme() as series_theme:
                with dpg.theme_component(dpg.mvBarSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, layer.color, category=dpg.mvThemeCat_Plots)

            dpg.bind_item_theme(series_tag, series_theme)

        self._update_axes_limits()

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
