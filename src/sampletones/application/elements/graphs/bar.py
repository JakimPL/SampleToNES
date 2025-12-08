from typing import Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.typehints import Color, Sender

from ...constants.graphs import (
    COL_BAR_PLOT_ZERO_LINE,
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_PLOT_LABEL_BAR,
    SUF_BAR_PLOT_HOVER_BAR,
    SUF_BAR_PLOT_ZERO_LINE,
    VAL_BAR_PLOT_HOVER_ALPHA,
    VAL_BAR_PLOT_MAX_Y,
    VAL_BAR_PLOT_MIN_X,
    VAL_BAR_PLOT_MIN_Y,
    VAL_BAR_PLOT_ZERO_LINE_THICKNESS,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_X,
)
from ...utils.dpg import (
    dpg_bind_item_theme,
    dpg_configure_item,
    dpg_delete_children,
    dpg_delete_item,
)
from .graph import GUIGraph
from .layers.bar import BarLayer


class GUIBarGraph(GUIGraph):
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
        label: str = LBL_PLOT_LABEL_BAR,
        x_min: float = VAL_MIN_GRAPH_DEFAULT_X,
        x_max: float = VAL_MAX_GRAPH_DEFAULT_X,
        y_min: float = VAL_BAR_PLOT_MIN_Y,
        y_max: float = VAL_BAR_PLOT_MAX_Y,
    ):
        self.current_data: Optional[np.ndarray] = None
        self.y_ticks: Optional[Tuple[int, ...]] = None
        self.zero_line_tag = f"{tag}{SUF_BAR_PLOT_ZERO_LINE}"
        self.hover_bar_tag = f"{tag}{SUF_BAR_PLOT_HOVER_BAR}"
        self.hovered_bar_index: Optional[int] = None
        self.hovered_bar_value: Optional[float] = None

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

    def _create_content(self) -> None:
        with dpg.plot(
            tag=self.plot_tag,
            label=self.label,
            height=self.height,
            width=self.width,
            anti_aliased=True,
        ):
            dpg.add_plot_legend(tag=self.legend_tag, location=dpg.mvPlot_Location_NorthEast)
            dpg.add_plot_axis(dpg.mvXAxis, tag=self.x_axis_tag)
            dpg.add_plot_axis(dpg.mvYAxis, tag=self.y_axis_tag)

        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self._mouse_move_callback)

    def load_data(
        self,
        data: np.ndarray,
        name: str,
        color: Color,
        y_ticks: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self.clear_layers()
        self.current_data = data
        self.y_ticks = y_ticks

        self.add_layer(BarLayer(data=data, name=name, color=color))

        self.x_min = VAL_BAR_PLOT_MIN_X
        self.x_max = float(len(data))

        self._update_axes_limits()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_children(self.y_axis_tag)
        for layer in self.layers.values():
            series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}"
            dpg.add_bar_series(
                layer.x_data,
                layer.y_data,
                # label=layer.name,
                parent=self.y_axis_tag,
                tag=series_tag,
                weight=layer.bar_weight,
            )

            with dpg.theme() as series_theme:
                with dpg.theme_component(dpg.mvBarSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Fill, layer.color, category=dpg.mvThemeCat_Plots)

            dpg_bind_item_theme(series_tag, series_theme)

        self._add_zero_line()
        self._add_hover_bar()
        self._update_axes_limits()

    def _add_hover_bar(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_item(self.hover_bar_tag)

        if self.hovered_bar_index is None or self.hovered_bar_value is None or self.current_data is None:
            return

        bar_x = float(self.hovered_bar_index) + 0.5
        bar_y = self.hovered_bar_value

        dpg.add_bar_series(
            [bar_x],
            [bar_y],
            parent=self.y_axis_tag,
            tag=self.hover_bar_tag,
            weight=0.8,
        )

        layer = next(iter(self.layers.values()))
        hover_color = (layer.color[0], layer.color[1], layer.color[2], VAL_BAR_PLOT_HOVER_ALPHA)

        with dpg.theme() as hover_theme:
            with dpg.theme_component(dpg.mvBarSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Fill, hover_color, category=dpg.mvThemeCat_Plots)

        dpg_bind_item_theme(self.hover_bar_tag, hover_theme)

    def _mouse_move_callback(self, sender: Sender, app_data: Tuple[int, int]) -> None:
        if not dpg.is_item_hovered(self.plot_tag) or self.current_data is None:
            if self.hovered_bar_index is not None:
                self.hovered_bar_index = None
                self.hovered_bar_value = None
                self._add_hover_bar()
            return

        plot_mouse_pos = dpg.get_plot_mouse_pos()
        if not plot_mouse_pos:
            return

        mouse_x = plot_mouse_pos[0]
        mouse_y = plot_mouse_pos[1]

        bar_index = int(mouse_x)
        if bar_index < 0 or bar_index >= len(self.current_data):
            if self.hovered_bar_index is not None:
                self.hovered_bar_index = None
                self.hovered_bar_value = None
                self._add_hover_bar()
            return

        clamped_y = np.clip(mouse_y, self.y_min, self.y_max)

        if self.hovered_bar_index != bar_index or self.hovered_bar_value != clamped_y:
            self.hovered_bar_index = bar_index
            self.hovered_bar_value = clamped_y
            self._add_hover_bar()

    def _add_zero_line(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        dpg_delete_item(self.zero_line_tag)

        dpg.add_line_series(
            [self.x_min, self.x_max],
            [0.0, 0.0],
            parent=self.y_axis_tag,
            tag=self.zero_line_tag,
        )

        with dpg.theme() as zero_line_theme:
            with dpg.theme_component(dpg.mvLineSeries):
                dpg.add_theme_color(dpg.mvPlotCol_Line, COL_BAR_PLOT_ZERO_LINE, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(
                    dpg.mvPlotStyleVar_LineWeight,
                    VAL_BAR_PLOT_ZERO_LINE_THICKNESS,
                    category=dpg.mvThemeCat_Plots,
                )

        dpg_bind_item_theme(self.zero_line_tag, zero_line_theme)

    def _update_axes_limits(self) -> None:
        dpg.set_axis_limits(self.x_axis_tag, self.x_min, self.x_max)
        dpg.set_axis_limits(self.y_axis_tag, self.y_min, self.y_max)
        dpg_configure_item(self.zero_line_tag, x=[self.x_min, self.x_max], y=[0.0, 0.0])

        if self.y_ticks is not None:
            tick_labels = [str(val) for val in self.y_ticks]
            dpg.set_axis_ticks(self.y_axis_tag, tuple(zip(tick_labels, self.y_ticks)))
