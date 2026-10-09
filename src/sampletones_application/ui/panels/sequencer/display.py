from typing import Dict, Final, Literal, Optional, Tuple

from sampletones_application.ui.elements.table.cells import pending_label
from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import (
    SequencerCellViewModel,
    SequencerRowViewModel,
)
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id, display_pitch, display_volume

CellKey = Tuple[int, Optional[ChannelName], SubColumn]
CellValues = Dict[CellKey, str]
CellKinds = Dict[CellKey, Optional[VoiceKind]]
NumberSubColumn = Literal[SubColumn.VOICE, SubColumn.VOLUME]

CELL_TITLE_SEPARATOR: Final[str] = " | "

_DEFAULT_LABELS: Final[Dict[SubColumn, str]] = {
    SubColumn.VOICE: display_id(None),
    SubColumn.TRANSPOSE: display_pitch(None),
    SubColumn.VOLUME: display_volume(None),
}


def indexed_label(index: int, label: str) -> str:
    """Joins a formatted index and a label into one display string, e.g. ``"03 Bass"``."""
    return f"{display_id(index)} {label}"


def cell_title(index: int, label: str) -> str:
    """Names the cell a menu was raised on, e.g. ``"0C | Pulse 1"``.

    Both grids title their cell menus this way: where along the grid the cell sits, then the
    channel it belongs to, so a menu states its target the same wherever it is opened.
    """
    return f"{display_id(index)}{CELL_TITLE_SEPARATOR}{label}"


def cell_display(cell_view_model: SequencerCellViewModel, subcolumn: SubColumn) -> str:
    """Extract the pre-formatted display string for one subcolumn from a cell view model."""
    match subcolumn:
        case SubColumn.VOICE:
            return cell_view_model.voice
        case SubColumn.TRANSPOSE:
            return cell_view_model.transpose
        case SubColumn.VOLUME:
            return cell_view_model.volume


def row_values(row: SequencerRowViewModel) -> Dict[TrackerSlot, str]:
    """What every slot of one tracker row reads, the Sample column's summaries among them."""
    values: Dict[TrackerSlot, str] = {
        TrackerSlot(None, SubColumn.VOICE): row.sample,
        TrackerSlot(None, SubColumn.TRANSPOSE): row.transpose,
        TrackerSlot(None, SubColumn.VOLUME): row.volume,
    }
    for channel in ChannelName.items():
        for subcolumn in SubColumn:
            values[TrackerSlot(channel, subcolumn)] = cell_display(row.cells[channel], subcolumn)

    return values


def row_kinds(row: SequencerRowViewModel) -> Dict[TrackerSlot, Optional[VoiceKind]]:
    """The kind of voice each voice slot of one tracker row names, which is the color that slot wears.

    Only the voice slot reports a kind, so the map covers those slots alone.
    """
    kinds: Dict[TrackerSlot, Optional[VoiceKind]] = {TrackerSlot(None, SubColumn.VOICE): row.sample_kind}
    for channel in ChannelName.items():
        kinds[TrackerSlot(channel, SubColumn.VOICE)] = row.cells[channel].kind

    return kinds


def format_committed(subcolumn: NumberSubColumn, value: Optional[int]) -> str:
    """Format a number as the display string stored in the optimistic cell cache.

    A pitch prints through :func:`display_pitch`, since the cell holds a note or a step.
    """
    match subcolumn:
        case SubColumn.VOICE:
            return display_id(value)
        case SubColumn.VOLUME:
            return display_volume(value)


def subcolumn_label(
    row: int,
    channel: Optional[ChannelName],
    subcolumn: SubColumn,
    *,
    cursor: Optional[TrackerCursor],
    pending: str,
    cell_values: CellValues,
) -> str:
    is_active = cursor is not None and cursor.row == row and cursor.channel == channel and cursor.subcolumn == subcolumn
    stored = cell_values.get(
        (row, channel, subcolumn),
        _DEFAULT_LABELS[subcolumn],
    )
    if is_active:
        return pending_label(
            pending,
            stored,
            len(_DEFAULT_LABELS[subcolumn]),
        )

    return stored
