from typing import Optional

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.instruments.note_off import NoteOff
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.song_position import SongPosition


def resolve_row(
    song: Song,
    position: SongPosition,
    channel_name: ChannelName,
) -> Optional[Row]:
    """The row one channel reaches at a position in the order.

    A position answers with a row where the order plays a pattern on that channel and the
    pattern is long enough to hold the row; anywhere else the channel plays on with whatever
    it already carries.

    Args:
        song: The arrangement being played.
        position: The order frame and the row within it.
        channel_name: The channel whose pattern is read.

    Returns:
        Optional[Row]: The row the channel reaches, or ``None`` where it reaches none.
    """
    if position.order_position >= song.order_length():
        return None

    order_entry = song.order[position.order_position].get(channel_name)
    if order_entry is None:
        return None

    pattern = song.pattern(channel_name, order_entry)
    if pattern is None or position.row_index >= len(pattern.rows):
        return None

    return pattern.rows[position.row_index]


def apply_row(performance: ChannelPerformance, row: Row) -> bool:
    """Moves a channel onto the row it has reached, and reports whether the note starts over.

    A note column names the sample to sound and begins it, taking the transpose and volume the
    row states or the defaults where it states neither. A row naming no note leaves the sample
    playing and changes only the columns it fills in, which is how a transpose or a volume bends
    a note already sounding.

    Args:
        performance: What the channel carries; updated in place.
        row: The row the channel reached.

    Returns:
        bool: Whether the channel starts over, which is where a phase-continuous voice resets.
    """
    match row.command:
        case Instrument() as instrument:
            performance.sample_id = instrument.sample_id
            performance.tick_index = 0
            performance.transpose = row.transpose if row.transpose is not None else 0
            performance.volume = row.volume if row.volume is not None else MAX_VOLUME
            return True
        case NoteOff():
            performance.sample_id = None
            performance.tick_index = 0
            return True
        case None:
            if row.transpose is not None:
                performance.transpose = row.transpose

            if row.volume is not None:
                performance.volume = row.volume

            return False
