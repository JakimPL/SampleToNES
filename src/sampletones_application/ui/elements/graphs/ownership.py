from typing import Dict, List, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.general.colors.stem import StemColors
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.graphs import (
    SUF_GRAPH_THEME,
    SUF_OWNERSHIP_HEARD,
    SUF_OWNERSHIP_LEFT_OUT,
    SUF_OWNERSHIP_RUN,
)
from sampletones_application.utils.gui.dpg import dpg_bind_item_theme, dpg_delete_item
from sampletones_application.utils.gui.palette.dpg import dpg_add_palette_theme_color
from sampletones_application.view_model.shared.ownership import OwnershipRunViewModel


class OwnershipRuns:
    """Paints the recordings behind a stretch of a plot, each run a flat bar in its own color.

    Two surfaces show a frame's owner — the ribbon under the waveform and the stretch under an
    instrument's bars — so both paint through this, and a recording is one color wherever it is
    shown. Each surface states the span its own axis counts in and the band the bars sit in, so
    the same runs land under a waveform read in samples and under an envelope read in frames.

    A theme is named after the reading it paints — the recording, the place it stands on the
    record and whether the reader hears it — so two stretches of one reading share a theme
    however many times a document divides, and a name reads the same from one run of the
    application to the next.
    """

    def __init__(self, stem_colors: StemColors) -> None:
        self._stem_colors = stem_colors
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
        self._clear(y_axis_tag)
        bottom, top = band
        painted: List[str] = []
        for run in runs:
            series_tag = compose_tag(y_axis_tag, SUF_OWNERSHIP_RUN, str(run.start_frame))
            dpg.add_shade_series(
                [run.start_frame * frame_span, run.end_frame * frame_span],
                y1=[bottom, bottom],
                y2=[top, top],
                tag=series_tag,
                parent=y_axis_tag,
            )
            self._bind(series_tag, run)
            painted.append(series_tag)

        self._painted[y_axis_tag] = painted

    def _clear(self, y_axis_tag: str) -> None:
        """Takes the stretches this axis carries away, which is what a repaint begins with."""
        for series_tag in self._painted.pop(y_axis_tag, []):
            dpg_delete_item(series_tag)

    def _bind(self, series_tag: str, run: OwnershipRunViewModel) -> None:
        """Binds the run its recording's fill, through the theme every like reading shares."""
        theme_tag = compose_tag(
            SUF_OWNERSHIP_RUN,
            SUF_GRAPH_THEME,
            str(run.stem_id),
            str(run.position),
            SUF_OWNERSHIP_HEARD if run.heard else SUF_OWNERSHIP_LEFT_OUT,
        )
        if not dpg.does_item_exist(theme_tag):
            color = self._stem_colors.for_stem(run.stem_id, run.position, heard=run.heard)
            with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvShadeSeries):
                dpg_add_palette_theme_color(dpg.mvPlotCol_Fill, color, category=dpg.mvThemeCat_Plots)

        dpg_bind_item_theme(series_tag, theme_tag)
