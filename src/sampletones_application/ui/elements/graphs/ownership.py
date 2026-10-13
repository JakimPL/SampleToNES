from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

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
from sampletones_application.view_model.shared.ownership import (
    OwnershipRunViewModel,
    OwnerStretchesViewModel,
    runs_by_owner,
)

Stretches = Tuple[Tuple[int, int], ...]
Band = Tuple[float, float]
Geometry = Tuple[Stretches, float, Band]


def traced(
    stretches: Stretches,
    frame_span: float,
    band: Band,
) -> Tuple[List[float], List[float], List[float]]:
    """The points one shade series runs through to fill ``stretches`` and nothing between them.

    The series rises to the band's top at the start of each stretch and falls back to its bottom at
    the end, so the fill between its two edges covers the stretches alone and has no height anywhere
    else.

    Args:
        stretches: The first frame and the frame one past the last of each stretch, in frame order.
        frame_span: What one frame measures on the axis the plot counts along.
        band: The lower and upper edge the stretches are drawn between.

    Returns:
        Tuple[List[float], List[float], List[float]]: The positions along the axis, the lower edge at
        each, and the upper edge at each.
    """
    bottom, top = band
    positions: List[float] = []
    upper: List[float] = []
    for start, end in stretches:
        left, right = start * frame_span, end * frame_span
        positions.extend((left, left, right, right))
        upper.extend((bottom, top, top, bottom))

    return positions, [bottom] * len(positions), upper


@dataclass(frozen=True)
class _Painted:
    """One recording's series on an axis, with what it was traced from and how it is heard."""

    series_tag: str
    geometry: Geometry
    heard: bool


class OwnershipRuns:
    """Paints the recordings behind a stretch of a plot, each recording one flat series in its own color.

    Two surfaces show a frame's owner — the ribbon under the waveform and the stretch under an
    instrument's bars — so both paint through this, and a recording is one color wherever it is
    shown. Each surface states the span its own axis counts in and the band the bars sit in, so
    the same runs land under a waveform read in samples and under an envelope read in frames.

    A recording's stretches along one lane are one series traced over them, so a lane costs as many
    series as it has owners however many times the document divides. A repaint touches a series only
    where something changed: its points are traced again where the stretches moved, and its theme is
    bound again where the reader's hearing of the recording changed, so a box on the stems card
    repaints as a few theme bindings.

    A theme is named after the reading it paints — the recording and whether the reader hears it —
    so two stretches of one reading share a theme however many times a document divides, and a name
    reads the same from one run of the application to the next.
    """

    def __init__(self, stem_colors: StemColors) -> None:
        self._stem_colors = stem_colors
        self._painted: Dict[str, Dict[int, _Painted]] = {}

    def paint(
        self,
        y_axis_tag: str,
        runs: Sequence[OwnershipRunViewModel],
        *,
        frame_span: float,
        band: Band,
    ) -> None:
        """Draws one lane's stretches into an axis.

        Args:
            y_axis_tag: The axis the stretches are drawn on.
            runs: The stretches, in frame order.
            frame_span: What one frame measures on the axis the plot counts along.
            band: The lower and upper edge the stretches are drawn between.
        """
        owners = runs_by_owner(runs)
        painted = self._painted.setdefault(y_axis_tag, {})
        for stem_id in [stem_id for stem_id in painted if stem_id not in owners]:
            dpg_delete_item(painted.pop(stem_id).series_tag)

        for stem_id, owner in owners.items():
            painted[stem_id] = self._paint_owner(y_axis_tag, painted.get(stem_id), owner, frame_span, band)

    def _paint_owner(
        self,
        y_axis_tag: str,
        standing: Optional[_Painted],
        owner: OwnerStretchesViewModel,
        frame_span: float,
        band: Band,
    ) -> _Painted:
        """Brings one recording's series on the axis to ``owner``, drawing it where the axis holds none."""
        series_tag = compose_tag(y_axis_tag, SUF_OWNERSHIP_RUN, str(owner.stem_id))
        geometry: Geometry = (owner.stretches, frame_span, band)
        if standing is not None and not dpg.does_item_exist(series_tag):
            standing = None

        if standing is None:
            positions, lower, upper = traced(owner.stretches, frame_span, band)
            dpg.add_shade_series(positions, lower, y2=upper, tag=series_tag, parent=y_axis_tag)
        elif standing.geometry != geometry:
            positions, lower, upper = traced(owner.stretches, frame_span, band)
            dpg.configure_item(series_tag, x=positions, y1=lower, y2=upper)

        if standing is None or standing.heard != owner.heard:
            self._bind(series_tag, owner.stem_id, owner.heard)

        return _Painted(series_tag=series_tag, geometry=geometry, heard=owner.heard)

    def _bind(self, series_tag: str, stem_id: int, heard: bool) -> None:
        """Binds the series its recording's fill, through the theme every like reading shares."""
        theme_tag = compose_tag(
            SUF_OWNERSHIP_RUN,
            SUF_GRAPH_THEME,
            str(stem_id),
            SUF_OWNERSHIP_HEARD if heard else SUF_OWNERSHIP_LEFT_OUT,
        )
        if not dpg.does_item_exist(theme_tag):
            color = self._stem_colors.for_stem(stem_id, heard=heard)
            with dpg.theme(tag=theme_tag), dpg.theme_component(dpg.mvShadeSeries):
                dpg_add_palette_theme_color(dpg.mvPlotCol_Fill, color, category=dpg.mvThemeCat_Plots)

        dpg_bind_item_theme(series_tag, theme_tag)
