from typing import Dict, List, Mapping

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.layout.graphs import GraphsLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import SUF_GRAPH_THEME, SUF_RIBBON_GROUND
from sampletones_application.ui.elements.graphs.ownership import OwnershipRuns
from sampletones_application.utils.gui.dpg import dpg_bind_item_theme
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.view_model.shared.ownership import OwnershipRibbonViewModel
from sampletones_core.constants.enums import ChannelName


class GUIOwnershipRibbon:
    """The recordings behind each stretch of the waveform, a lane of flat bars per channel.

    Each lane stands for one channel in play and runs the length of the document beneath the
    waveform, painted in the color of the recording holding each stretch. A resting stretch shows
    the ground the lane is laid on, so a reader tells at a glance which recording carried a
    passage and where nothing was played. The lanes are drawn only while more than one recording
    is in play, since a document answering to a single recording has nothing to distinguish.

    A lane is painted into the row the waveform keeps for its channel, which is what holds the
    two to one span: they begin and end together however wide the amplitude labels beside them
    run, a stretch stands under the sound it names through every zoom, and the row prints the
    channel's own letter beside it.
    """

    def __init__(
        self,
        *,
        plot_tags: Mapping[ChannelName, str],
        y_axis_tags: Mapping[ChannelName, str],
        layout: GraphsLayout,
        stem_colors: StemColors,
    ) -> None:
        self._plot_tags = dict(plot_tags)
        self._y_axis_tags = dict(y_axis_tags)
        self._layout = layout
        self._stem_colors = stem_colors
        self._view_model: OwnershipRibbonViewModel = OwnershipRibbonViewModel.empty()
        self._runs = OwnershipRuns(stem_colors)

    def bind_theme(self) -> None:
        """Lays each lane's ground, which is the color a resting stretch shows."""
        for channel_name, plot_tag in self._plot_tags.items():
            theme_tag = compose_tag(plot_tag, SUF_GRAPH_THEME, SUF_RIBBON_GROUND)
            with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvPlot):
                dpg_add_palette_theme_color(
                    dpg.mvPlotCol_PlotBg,
                    self._stem_colors.rest,
                    category=dpg.mvThemeCat_Plots,
                )

            dpg_bind_item_theme(self._y_axis_tags[channel_name], theme_tag)

    def update_view(self, view_model: OwnershipRibbonViewModel) -> None:
        """Repaints the lanes for what the reader is listening to."""
        self._view_model = view_model
        drawn = {lane.channel_name: lane for lane in view_model.lanes}
        bottom = self._layout.ribbon.lane_gap / 2.0
        for channel_name, y_axis_tag in self._y_axis_tags.items():
            if not dpg.does_item_exist(y_axis_tag):
                continue

            lane = drawn.get(channel_name)
            self._runs.paint(
                y_axis_tag,
                lane.runs if lane is not None else (),
                frame_span=view_model.frame_length,
                band=(bottom, 1.0 - bottom),
            )
            dpg.set_axis_limits(y_axis_tag, 0.0, 1.0)
            dpg.set_axis_limits_constraints(y_axis_tag, 0.0, 1.0)

    def clear(self) -> None:
        """Empties the lanes, which is what closing the document they describe does."""
        self.update_view(OwnershipRibbonViewModel.empty())

    @property
    def lane_heights(self) -> Dict[ChannelName, int]:
        """The height each channel's row takes, which is nothing where it has no lane to show."""
        drawn = self.lane_channels if self._view_model.is_drawn else []
        return {
            channel_name: self._layout.ribbon.lane_height if channel_name in drawn else 0
            for channel_name in ChannelName.items()
        }

    @property
    def lane_channels(self) -> List[ChannelName]:
        """The channels the lanes stand for, in the order they are drawn."""
        return [lane.channel_name for lane in self._view_model.lanes]
