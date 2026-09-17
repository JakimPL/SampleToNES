from typing import Dict, Final, List

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import (
    SUF_GRAPH_THEME,
    SUF_RIBBON_LANE,
    SUF_RIBBON_RUN,
)
from sampletones_application.utils.gui.dpg import dpg_delete_children
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.view_model.shared.ownership import (
    OwnershipLaneViewModel,
    OwnershipRibbonViewModel,
)

SINGLE_LANE: Final[float] = 1.0


class GUIOwnershipRibbon:
    """The recordings behind each stretch of the waveform, a lane of flat bars per channel.

    Each lane stands for one channel in play and runs the length of the document beneath the
    waveform, painted in the color of the recording holding each stretch. A resting stretch shows
    the ground the lane is laid on, so a reader tells at a glance which recording carried a
    passage and where nothing was played. The lanes are drawn only while more than one recording
    is in play, since a document answering to a single recording has nothing to distinguish.

    The lanes are painted into the row the waveform keeps for them, which is what holds the two
    to one span: they begin and end together however wide the amplitude labels beside them run,
    and a stretch stands under the sound it names through every zoom.
    """

    def __init__(
        self,
        *,
        plot_tag: str,
        y_axis_tag: str,
        layout: GraphsLayout,
        stem_colors: StemColors,
    ) -> None:
        self._plot_tag = plot_tag
        self._y_axis_tag = y_axis_tag
        self._layout = layout
        self._stem_colors = stem_colors
        self._view_model: OwnershipRibbonViewModel = OwnershipRibbonViewModel.empty()
        self._run_themes: Dict[BaseColor, str] = {}

    def bind_theme(self) -> None:
        """Lays the lanes edge to edge, so they read as flat bars rather than as a chart."""
        theme_tag = compose_tag(self._plot_tag, SUF_GRAPH_THEME)
        with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_style(dpg.mvPlotStyleVar_PlotPadding, 0, 0, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)
            dpg_add_palette_theme_color(
                dpg.mvPlotCol_PlotBg,
                self._stem_colors.rest,
                category=dpg.mvThemeCat_Plots,
            )

        dpg.bind_item_theme(self._plot_tag, theme_tag)

    def update_view(self, view_model: OwnershipRibbonViewModel) -> None:
        """Repaints the lanes for what the reader is listening to."""
        self._view_model = view_model
        if not dpg.does_item_exist(self._y_axis_tag):
            return

        dpg_delete_children(self._y_axis_tag)
        for index, lane in enumerate(view_model.lanes):
            self._draw_lane(index, lane, view_model)

        lanes = float(len(view_model.lanes)) or SINGLE_LANE
        dpg.set_axis_limits(self._y_axis_tag, 0.0, lanes)
        dpg.set_axis_limits_constraints(self._y_axis_tag, 0.0, lanes)

    def clear(self) -> None:
        """Empties the lanes, which is what closing the document they describe does."""
        self.update_view(OwnershipRibbonViewModel.empty())

    @property
    def height(self) -> int:
        """The height the lanes need, which is nothing while there is nothing to tell apart."""
        if not self._view_model.is_drawn:
            return 0

        return self._layout.ribbon.height(len(self._view_model.lanes))

    @property
    def lane_channels(self) -> List[str]:
        """The channels the lanes stand for, in the order they are drawn."""
        return [lane.channel_name.value for lane in self._view_model.lanes]

    def _draw_lane(
        self,
        index: int,
        lane: OwnershipLaneViewModel,
        view_model: OwnershipRibbonViewModel,
    ) -> None:
        """Paints one channel's stretches, each run a flat bar in its recording's color."""
        top = float(len(view_model.lanes) - index)
        bottom = top - 1.0 + self._layout.ribbon.lane_gap
        for run in lane.runs:
            series_tag = compose_tag(
                self._y_axis_tag,
                SUF_RIBBON_LANE,
                str(index),
                SUF_RIBBON_RUN,
                str(run.start_frame),
            )
            dpg.add_shade_series(
                [
                    run.start_frame * view_model.frame_length,
                    run.end_frame * view_model.frame_length,
                ],
                y1=[bottom, bottom],
                y2=[top, top],
                tag=series_tag,
                parent=self._y_axis_tag,
            )
            self._bind_run_theme(series_tag, self._stem_colors.for_stem(run.stem_id, run.position))

    def _bind_run_theme(self, series_tag: str, color: BaseColor) -> None:
        """Binds the run its recording's fill, reusing the theme two runs of one color share."""
        theme_tag = self._run_themes.get(color)
        if theme_tag is None:
            theme_tag = compose_tag(self._plot_tag, SUF_GRAPH_THEME, str(len(self._run_themes)))
            with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvShadeSeries):
                dpg_add_palette_theme_color(dpg.mvPlotCol_Fill, color, category=dpg.mvThemeCat_Plots)

            self._run_themes[color] = theme_tag

        dpg.bind_item_theme(series_tag, theme_tag)
