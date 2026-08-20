from typing import Final, Optional

from sampletones_application.layout.tabs.sequencer.colors.channel import ChannelColors
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_core.constants.enums import ChannelName

_LEADING_TABLE_COLUMNS: Final[int] = 2
SAMPLE_TABLE_COLUMN: Final[int] = _LEADING_TABLE_COLUMNS
DIVIDER_TABLE_COLUMN: Final[int] = SAMPLE_TABLE_COLUMN + 1
_FIRST_CHANNEL_TABLE_COLUMN: Final[int] = DIVIDER_TABLE_COLUMN + 1
_TRAILING_TABLE_COLUMNS: Final[int] = 1
TRACKER_TABLE_COLUMNS: Final[int] = _FIRST_CHANNEL_TABLE_COLUMN + len(ChannelName.items()) + _TRAILING_TABLE_COLUMNS

HEADER_TABLE_ROW: Final[int] = 0
HEADER_TABLE_ROWS: Final[int] = HEADER_TABLE_ROW + 1


def channel_color(colors: ChannelColors, channel: ChannelName) -> BaseColor:
    match channel:
        case ChannelName.PULSE1:
            return colors.pulse1
        case ChannelName.PULSE2:
            return colors.pulse2
        case ChannelName.TRIANGLE:
            return colors.triangle
        case ChannelName.NOISE:
            return colors.noise


def tracker_table_column(channel: Optional[ChannelName]) -> int:
    """Maps a logical column to its DPG table column index.

    The visual divider between the sample column and the channels occupies a table
    column of its own, so the channels sit one slot further right than their
    logical position. The divider is purely visual, so :data:`CHANNEL_AXIS` covers
    only the cursor-addressable columns.
    """
    if channel is None:
        return SAMPLE_TABLE_COLUMN

    return _FIRST_CHANNEL_TABLE_COLUMN + ChannelName.items().index(channel)


def tracker_table_row(row_index: int) -> int:
    """Maps a pattern row to its DPG table row index.

    The clickable header row occupies the table's first row, so a pattern row sits one
    slot further down than its index. Every highlight keyed by table row goes through
    here, keeping the cursor, hover, and playback cues on the row the user sees.
    """
    return row_index + HEADER_TABLE_ROWS
