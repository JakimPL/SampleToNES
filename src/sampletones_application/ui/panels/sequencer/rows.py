from dataclasses import dataclass
from typing import Optional

from sampletones_application.layout.tabs.sequencer.colors.colors import SequencerColors
from sampletones_application.layout.tabs.sequencer.tracker.tracker import TrackerLayout
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.layered import LayeredColor


@dataclass(frozen=True)
class RowCues:
    """The pattern rows the tracker's moving marks stand on."""

    cursor: Optional[int]
    playing: Optional[int]


def group_color(
    row_index: int,
    tracker: TrackerLayout,
    colors: SequencerColors,
) -> Optional[BaseColor]:
    """The emphasis a row takes from the group it opens.

    A row opening a bar takes the stronger of the two shades, since a bar boundary is also a
    beat boundary. A row inside a beat keeps the zebra stripe it already has.
    """
    if tracker.rows_per_bar > 0 and row_index % tracker.rows_per_bar == 0:
        return colors.rows.bar

    if tracker.rows_per_beat > 0 and row_index % tracker.rows_per_beat == 0:
        return colors.rows.beat

    return None


def cue_color(
    row_index: int,
    cues: RowCues,
    colors: SequencerColors,
) -> Optional[BaseColor]:
    """The mark a row carries while the song plays or the cursor rests on it.

    The playing row outranks the cursor row, so a passing playhead stays legible over the
    row being edited; the cursor keeps its cell mark either way.
    """
    if cues.playing == row_index:
        return colors.playback_row

    if cues.cursor == row_index:
        return colors.cursor_row

    return None


def row_background(
    row_index: int,
    tracker: TrackerLayout,
    colors: SequencerColors,
    cues: RowCues,
) -> Optional[BaseColor]:
    """The colour a pattern row's background carries, group and cue taken together.

    DearPyGui offers one row background above the zebra stripe, so the row's standing
    emphasis and whatever mark is passing over it arrive as a single shade: the cue is
    composed over the group the row belongs to. A plain row with no mark on it returns
    ``None``, leaving the stripe as it is.
    """
    group = group_color(row_index, tracker, colors)
    cue = cue_color(row_index, cues, colors)
    if group is None:
        return cue

    if cue is None:
        return group

    return LayeredColor(base=group, overlay=cue)
