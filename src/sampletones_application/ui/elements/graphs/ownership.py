from typing import Dict, List, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.tags.compose import compose_tag, identity_part
from sampletones_application.tags.graphs import SUF_GRAPH_THEME, SUF_RIBBON_RUN
from sampletones_application.utils.gui.dpg import dpg_bind_item_theme, dpg_delete_item
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.view_model.shared.ownership import OwnershipRunViewModel


class OwnershipRuns:
    """Paints the recordings behind a stretch of a plot, each run a flat bar in its own color.

    Two surfaces show a frame's owner — the ribbon under the waveform and the stretch under an
    instrument's bars — so both paint through this, and a recording is one color wherever it is
    shown. Each surface states the span its own axis counts in and the band the bars sit in, so
    the same runs land under a waveform read in samples and under an envelope read in frames.

    Two runs of one color share a theme, since a document may divide into many stretches and each
    theme is an item DearPyGui keeps for the life of the context. A theme is named after the
    color it fills with, so the surfaces painting a recording alike share one theme rather than
    racing for a name.
    """

    def __init__(self, stem_colors: StemColors) -> None:
        self._stem_colors = stem_colors
        self._themes: Dict[BaseColor, str] = {}
        self._painted: Dict[str, List[str]] = {}

    def paint(
        self,
        y_axis_tag: str,
        runs: Sequence[OwnershipRunViewModel],
        *,
        frame_span: float,
        band: Tuple[float, float],
    ) -> None:
        """Draws one lane's stretches into an axis.

        Args:
            y_axis_tag: The axis the stretches are drawn on.
            runs: The stretches, in frame order.
            frame_span: What one frame measures on the axis the plot counts along.
            band: The lower and upper edge the stretches are drawn between.
        """
        self.clear(y_axis_tag)
        bottom, top = band
        painted: List[str] = []
        for run in runs:
            series_tag = compose_tag(y_axis_tag, SUF_RIBBON_RUN, str(run.start_frame))
            dpg.add_shade_series(
                [run.start_frame * frame_span, run.end_frame * frame_span],
                y1=[bottom, bottom],
                y2=[top, top],
                tag=series_tag,
                parent=y_axis_tag,
            )
            self._bind(series_tag, self._stem_colors.for_stem(run.stem_id, run.position))
            painted.append(series_tag)

        self._painted[y_axis_tag] = painted

    def clear(self, y_axis_tag: str) -> None:
        """Takes the stretches this axis carries away, which is what a repaint begins with."""
        for series_tag in self._painted.pop(y_axis_tag, []):
            dpg_delete_item(series_tag)

    def _bind(self, series_tag: str, color: BaseColor) -> None:
        """Binds the run its recording's fill, reusing the theme two runs of one color share."""
        theme_tag = self._themes.get(color)
        if theme_tag is None:
            theme_tag = compose_tag(SUF_RIBBON_RUN, SUF_GRAPH_THEME, identity_part(repr(color)))
            if not dpg.does_item_exist(theme_tag):
                with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvShadeSeries):
                    dpg_add_palette_theme_color(dpg.mvPlotCol_Fill, color, category=dpg.mvThemeCat_Plots)

            self._themes[color] = theme_tag

        dpg_bind_item_theme(series_tag, theme_tag)
