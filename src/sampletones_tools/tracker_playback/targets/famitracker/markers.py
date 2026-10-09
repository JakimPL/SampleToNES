from typing import Final, Tuple

from sampletones_core.formats.famitracker.model.module import FamiTrackerModule, OrderFrame
from sampletones_core.formats.famitracker.model.pattern import PatternData, RowCell
from sampletones_core.formats.famitracker.specification.channels import ChannelId
from sampletones_core.formats.famitracker.specification.patterns import (
    EMPTY_INSTRUMENT,
    EMPTY_NOTE,
    EMPTY_VOLUME,
    MIN_OCTAVE,
    EffectId,
)

MARKER_LEVELS: Final[int] = 4


def row_marker(row_index: int) -> int:
    """The level the marker of a row loads: its place in the song, wrapped into ``MARKER_LEVELS``.

    Two rows in a row always carry different levels, so every row's marker is a new write. The
    DMC's level shifts how loud the triangle and the noise sound in the mix, and a jump between
    levels clicks, so low levels keep both slight.

    Args:
        row_index: The row's place in one pass through the song.

    Returns:
        int: The level, below ``MARKER_LEVELS``.
    """
    return row_index % MARKER_LEVELS


def marked_module(module: FamiTrackerModule) -> FamiTrackerModule:
    """The module with a row marker on every row of its DPCM channel, the channel the application's export leaves empty.

    Each order frame plays a DPCM pattern of its own, and each of its rows loads the DMC's output
    level with that row's marker. FamiTracker writes the level to ``$4011`` on the tick it plays the
    row, so the NSF it exports says where every row starts. The other channels stay as they are.

    Args:
        module: The module the application's export built.

    Returns:
        FamiTrackerModule: The module with the markers.
    """
    track = module.track
    rows = track.rows_per_pattern
    patterns = tuple(pattern for pattern in track.patterns if pattern.channel != ChannelId.DPCM)
    markers = tuple(_marker_pattern(frame, rows) for frame in range(len(track.order)))
    return module.model_copy(
        update={
            "track": track.model_copy(
                update={
                    "order": tuple(_marked_frame(frame, entries) for frame, entries in enumerate(track.order)),
                    "patterns": patterns + markers,
                }
            )
        }
    )


def _marked_frame(frame: int, entries: OrderFrame) -> OrderFrame:
    return tuple(frame if channel == ChannelId.DPCM else index for channel, index in zip(ChannelId, entries))


def _marker_pattern(frame: int, rows: int) -> PatternData:
    return PatternData(
        channel=ChannelId.DPCM,
        index=frame,
        rows=tuple(_marker_cell(row, row_marker(frame * rows + row)) for row in range(rows)),
    )


def _marker_cell(row: int, level: int) -> RowCell:
    effects: Tuple[Tuple[int, int], ...] = ((int(EffectId.DAC), level),)
    return RowCell(
        row_number=row,
        note=EMPTY_NOTE,
        octave=MIN_OCTAVE,
        instrument=EMPTY_INSTRUMENT,
        volume=EMPTY_VOLUME,
        effects=effects,
    )
