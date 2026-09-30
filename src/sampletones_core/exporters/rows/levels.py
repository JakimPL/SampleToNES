from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional, Set

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME, SILENT_VOLUME
from sampletones_core.performance.modifiers import triangle_sounds_at
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_on import NoteOn


@dataclass(frozen=True)
class RowPlace:
    """Where a row stands in the song, both as the order plays it and as the pattern pool holds it.

    Attributes:
        order_position: The frame of the order the row is played in.
        pattern_index: The pattern the frame plays on the row's channel.
        row_index: The row's position within that pattern.
    """

    order_position: int
    pattern_index: int
    row_index: int


@dataclass(frozen=True)
class LevelWalk:
    """One pass of a channel through the song, following the level a tracker's volume column carries.

    Attributes:
        full_level_notes: The notes stating no level that the pass reaches while the channel carries
            a level other than full.
        closing_volume: The level the channel carries once the pass reaches the end of the order.
    """

    full_level_notes: FrozenSet[RowPlace]
    closing_volume: int

    @classmethod
    def walk(
        cls,
        song: Song,
        channel_name: ChannelName,
        opening_volume: int,
    ) -> LevelWalk:
        """Walks one channel through the order from ``opening_volume``, frame by frame and row by row.

        A tracker's volume column keeps the last level a cell wrote, so a row that states a level
        sets it, and every other row leaves it where it stands. A note whose row states none starts
        at the full level in the song, and the export writes it there wherever the tracker carries
        another, so the channel stands at the full level after it either way. A note naming a voice
        with no instrument on the channel counts alike: the song sets the level there too, and the
        note cut the export writes in its place carries it.

        Args:
            song: The arrangement being exported.
            channel_name: The channel whose rows are walked.
            opening_volume: The level the channel carries into the first frame.

        Returns:
            LevelWalk: The notes reached below or above the full level, and the level the pass ends at.
        """
        volume = opening_volume
        notes: Set[RowPlace] = set()
        for order_position, frame in enumerate(song.order):
            pattern_index = frame.get(channel_name)
            if pattern_index is None:
                continue

            pattern = song.pattern(channel_name, pattern_index)
            if pattern is None:
                continue

            for row_index, row in enumerate(pattern.rows[: song.rows_per_pattern]):
                if cls._starts_at_full_level(row) and volume != MAX_VOLUME:
                    notes.add(
                        RowPlace(
                            order_position=order_position,
                            pattern_index=pattern_index,
                            row_index=row_index,
                        )
                    )

                volume = cls._volume_after(row, volume)

        return cls(full_level_notes=frozenset(notes), closing_volume=volume)

    @staticmethod
    def _starts_at_full_level(row: Row) -> bool:
        """Whether a row starts a note at the full level, which is a note-on stating no level of its own."""
        match row.command:
            case NoteOn():
                return row.volume is None
            case _:
                return False

    @staticmethod
    def _volume_after(row: Row, volume: int) -> int:
        """The level a tracker carries past one row: the level its cell writes, or the one it carried."""
        if row.volume is not None:
            return row.volume

        match row.command:
            case NoteOn():
                return MAX_VOLUME
            case _:
                return volume


def full_level_notes(song: Song, channel_name: ChannelName) -> FrozenSet[RowPlace]:
    """The notes of one channel whose cell writes the full level, so a tracker starts them where the song does.

    The song starts a note at the full level wherever its row states none, while a tracker's volume
    column carries the last level a cell wrote into every note after it. A note whose row states no
    level is therefore written at the full level wherever the tracker reaches it carrying another,
    which is where a user writing the song in the tracker would type one. A note the tracker
    reaches at the full level keeps its blank cell, so the document states a level only where the
    level changes.

    A tracker plays the order frame by frame and returns to the first frame at its end, keeping the
    level each channel was left at. The walk therefore passes through the song twice: from the full
    level a channel starts at, and from the level the song ends on. A pattern the order plays in
    several frames is reached in each of them.

    Args:
        song: The arrangement being exported.
        channel_name: The channel whose notes are found.

    Returns:
        FrozenSet[RowPlace]: The notes whose cell writes the full level.
    """
    opening = LevelWalk.walk(song, channel_name, MAX_VOLUME)
    looping = LevelWalk.walk(song, channel_name, opening.closing_volume)
    return opening.full_level_notes | looping.full_level_notes


def cell_volume(
    row: Row,
    channel_name: ChannelName,
    *,
    full_level: bool,
) -> Optional[int]:
    """The level a row's volume cell states, in the song's own terms.

    A row states its own level, a note :func:`full_level_notes` found states the full level, and any
    other row states none, so the tracker carries the level on. The triangle reads a level as
    whether it sounds: the song sounds it above half volume only, while both trackers sound it at
    any level above silence. A triangle row at a level the song rests at therefore states silence,
    and a row at a level it sounds at states that level.

    Args:
        row: The row being written.
        channel_name: The channel the row stands on.
        full_level: Whether the row is a note that writes the full level.

    Returns:
        Optional[int]: The level the cell states, or ``None`` where the cell stays empty.
    """
    volume = row.volume
    if volume is None and full_level:
        volume = MAX_VOLUME

    if volume is None:
        return None

    if channel_name == ChannelName.TRIANGLE and not triangle_sounds_at(volume):
        return SILENT_VOLUME

    return volume
