from typing import Callable, Optional, Tuple

import dearpygui.dearpygui as dpg
import numpy as np

from sampletones.typehints import Color, Sender

from ...constants.graphs import (
    DIM_GRAPH_HEIGHT,
    DIM_GRAPH_WIDTH,
    LBL_PLOT_LABEL_BAR,
    SUF_BAR_PLOT_HOVER_BAR,
    SUF_BAR_PLOT_MOUSE_HANDLER,
    SUF_BAR_PLOT_ZERO_LINE,
    SUF_GRAPH_THEME,
    VAL_BAR_PLOT_HOVER_ALPHA,
    VAL_MAX_GRAPH_DEFAULT_X,
    VAL_MAX_GRAPH_DEFAULT_Y,
    VAL_MIN_GRAPH_DEFAULT_X,
    VAL_MIN_GRAPH_DEFAULT_Y,
)
from ...themes.graphs.zero import ZeroLineGraphTheme
from ...themes.theme import Theme
from ...utils.dpg import (
    dpg_bind_item_theme,
    dpg_configure_item,
    dpg_delete_item,
    dpg_is_item_hovered,
)
from .graph import GUIGraph
from .layers.bar import BarLayer

OnBarPointClickedCallback = Callable[[np.ndarray], None]
OnBarPointHoveredCallback = Callable[[Optional[str], Optional[int]], None]


class GUIBarGraph(GUIGraph[BarLayer]):
    tag: str
    parent: str
    width: int
    height: int
    label: str

    def __init__(
        self,
        tag: str,
        parent: str,
        data_range: Tuple[int, int],
        width: int = DIM_GRAPH_WIDTH,
        height: int = DIM_GRAPH_HEIGHT,
        label: str = LBL_PLOT_LABEL_BAR,
        x_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_X, VAL_MAX_GRAPH_DEFAULT_X),
        y_range: Tuple[float, float] = (VAL_MIN_GRAPH_DEFAULT_Y, VAL_MAX_GRAPH_DEFAULT_Y),
        zero_line_theme: Theme = ZeroLineGraphTheme(),
    ):
        self.hover_bar_tag = f"{tag}{SUF_BAR_PLOT_HOVER_BAR}"
        self.hover_theme_tag = f"{self.hover_bar_tag}{SUF_GRAPH_THEME}"
        self.mouse_handler_tag = f"{tag}{SUF_BAR_PLOT_MOUSE_HANDLER}"

        self.zero_line_tag = f"{tag}{SUF_BAR_PLOT_ZERO_LINE}"
        self.zero_line_theme = zero_line_theme

        self.data_range = data_range
        self.y_ticks: Optional[Tuple[int, ...]] = None
        self.current_data: Optional[np.ndarray] = None

        self.on_bar_point_clicked: Optional[OnBarPointClickedCallback] = None
        self.on_bar_point_hovered: Optional[OnBarPointHoveredCallback] = None

        super().__init__(
            tag,
            parent,
            width,
            height,
            label,
            x_range,
            y_range,
        )

    def _create_content(self) -> None:
        with dpg.plot(
            tag=self.plot_tag,
            parent=self.tag,
            label=self.label,
            height=self.height,
            width=self.width,
            anti_aliased=True,
            no_box_select=True,
            pan_button=dpg.mvMouseButton_Middle,
            zoom_rate=self.zoom_factor,  # type: ignore
        ):
            dpg.add_plot_legend(tag=self.legend_tag, parent=self.plot_tag, location=dpg.mvPlot_Location_NorthEast)
            dpg.add_plot_axis(
                dpg.mvXAxis,
                tag=self.x_axis_tag,
                parent=self.plot_tag,
                auto_fit=False,
                range_fit=False,
            )
            dpg.add_plot_axis(
                dpg.mvYAxis,
                tag=self.y_axis_tag,
                parent=self.plot_tag,
                auto_fit=False,
                range_fit=False,
            )
            self._add_zero_line()

        self._bind_event_handler()
        self._update_axes_limits()

    def _setup_event_handler(self) -> None:
        super()._setup_event_handler()
        with dpg.handler_registry(tag=self.mouse_handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_mouse_action)
            dpg.add_mouse_click_handler(callback=self._on_mouse_action)

    def _bind_theme(
        self,
        layer: BarLayer,
        series_tag: str,
        theme_tag: str,
    ) -> None:
        if dpg.does_item_exist(theme_tag):
            return dpg_bind_item_theme(series_tag, theme_tag)

        with dpg.theme(tag=theme_tag):
            with dpg.theme_component(dpg.mvBarSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Fill,
                    layer.color,
                    category=dpg.mvThemeCat_Plots,
                )

        return dpg_bind_item_theme(series_tag, theme_tag)

    def _bind_hover_theme(self) -> None:
        if dpg.does_item_exist(self.hover_theme_tag):
            return dpg_bind_item_theme(self.hover_bar_tag, self.hover_theme_tag)

        layer = self._get_first_layer()
        if layer is None:
            raise RuntimeError("No layers available to bind hover theme")

        hover_color = (layer.color[0], layer.color[1], layer.color[2], VAL_BAR_PLOT_HOVER_ALPHA)
        with dpg.theme(tag=self.hover_theme_tag):
            with dpg.theme_component(dpg.mvBarSeries):
                dpg.add_theme_color(
                    dpg.mvPlotCol_Fill,
                    hover_color,
                    category=dpg.mvThemeCat_Plots,
                )

        return dpg_bind_item_theme(self.hover_bar_tag, self.hover_theme_tag)

    def load_data(
        self,
        data: np.ndarray,
        name: str,
        color: Color,
        y_ticks: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self._delete_hover_bar()
        self.clear_layers()
        self.current_data = data
        self.y_ticks = y_ticks
        self.add_layer(
            BarLayer(
                data=data,
                name=name,
                color=color,
            ),
        )

        self._add_hover_bar()
        self._update_ticks()
        self._update_ranges()

    def _set_layer(
        self,
        layer: BarLayer,
        series_tag: str,
        theme_tag: str,
    ) -> None:
        if dpg.does_item_exist(series_tag):
            dpg.configure_item(
                series_tag,
                x=layer.x_data,
                y=layer.y_data,
            )
        else:
            dpg.add_bar_series(
                layer.x_data.tolist(),
                layer.y_data.tolist(),
                tag=series_tag,
                parent=self.y_axis_tag,
                weight=layer.bar_weight,
            )

            self._bind_theme(layer, series_tag, theme_tag)
            self._update_ranges()

    def _update_ranges(self) -> None:
        x_min = -0.5
        x_max = 1.0 + max(
            (layer.x_data.max() for layer in self.layers.values() if layer.x_data.size > 0),
            default=VAL_MAX_GRAPH_DEFAULT_X,
        )
        self.x_range = (x_min, x_max)
        self._update_axes_limits()

    def _update_display(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag):
            return

        for layer in self.layers.values():
            series_tag = f"{self.y_axis_tag}_{layer.name.replace(' ', '_')}".lower()
            theme_tag = f"{series_tag}{SUF_GRAPH_THEME}"
            self._set_layer(layer, series_tag, theme_tag)

    def _add_hover_bar(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag) or not self._get_first_layer():
            return

        if dpg.does_item_exist(self.hover_bar_tag):
            self._set_hover_bar_position()
        else:
            dpg.add_bar_series(
                [0.5],
                [0.0],
                tag=self.hover_bar_tag,
                parent=self.y_axis_tag,
                weight=0.8,
            )

            self._bind_hover_theme()

    def _set_hover_bar_position(self, index: int = 0, value: float = 0.0) -> None:
        bar_x = float(index) + 0.5
        bar_y = round(value, 0)
        dpg_configure_item(
            self.hover_bar_tag,
            x=[bar_x],
            y=[bar_y],
        )

    def _delete_hover_bar(self) -> None:
        dpg_delete_item(self.hover_bar_tag)

    def _get_first_layer(self) -> Optional[BarLayer]:
        return next(iter(self.layers.values()), None)

    def _add_zero_line(self) -> None:
        if not dpg.does_item_exist(self.y_axis_tag) or dpg.does_item_exist(self.zero_line_tag):
            return

        dpg.add_inf_line_series(
            [0.0],
            parent=self.y_axis_tag,
            tag=self.zero_line_tag,
            horizontal=True,
        )

        self.zero_line_theme.bind_to_item(self.zero_line_tag)

    def _update_ticks(self) -> None:
        if self.y_ticks is not None:
            tick_labels = [str(val) for val in self.y_ticks]
            dpg.set_axis_ticks(self.y_axis_tag, tuple(zip(tick_labels, self.y_ticks)))

    def _on_mouse_action(self, sender: Sender, app_data: Tuple[int, int]) -> None:
        if (
            dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)
            or dpg.is_key_down(dpg.mvKey_LShift)
            or dpg.is_key_down(dpg.mvKey_RShift)
            or dpg.is_key_down(dpg.mvKey_LAlt)
            or dpg.is_key_down(dpg.mvKey_RAlt)
        ):
            return

        if not dpg_is_item_hovered(self.plot_tag) or self.current_data is None:
            self._set_hover_bar_position()
            return

        plot_mouse_pos = dpg.get_plot_mouse_pos()
        if not plot_mouse_pos:
            return

        mouse_x = plot_mouse_pos[0]
        mouse_y = plot_mouse_pos[1]
        bar_index = int(mouse_x)

        layer = self._get_first_layer()
        if layer is None:
            raise RuntimeError("A layer is expected to be present when handling mouse events")

        name = layer.name
        if bar_index < 0 or bar_index >= len(self.current_data):
            self.call(self.on_bar_point_hovered, name, None)
            return

        clamped_y = round(np.clip(mouse_y, *self.data_range))
        self._set_hover_bar_position(bar_index, clamped_y)
        self.call(self.on_bar_point_hovered, name, bar_index)

        if dpg.is_mouse_button_down(dpg.mvMouseButton_Left) or dpg.is_mouse_button_clicked(dpg.mvMouseButton_Left):
            layer.y_data[bar_index] = clamped_y
            self._update_display()
            self.call(self.on_bar_point_clicked, layer.y_data)
