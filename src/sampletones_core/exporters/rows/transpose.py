from __future__ import annotations

from dataclasses import dataclass, field
from typing import Container, Final, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.levels import RowPlace
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn

NOTE_TRANSPOSE: Final[int] = 0
NO_ROWS: Final[int] = 0


@dataclass(frozen=True)
class Repitch:
    """A row stating a transpose and no note, which moves the note sounding on its channel.

    The song keeps the voice where it stands, so the note goes on from the tick it reached, and every
    tick from this row on sounds at the transpose the row sets.

    Attributes:
        place: Where the row stands in the song.
        transpose: The transpose the row sets, measured from the voice's reference like a note-on's.
        rows: How many rows the note has sounded for when this row begins, counted across frames.
    """

    place: RowPlace
    transpose: int
    rows: int


@dataclass(frozen=True)
class SoundingNote:
    """A note-on the song sounds, with the transpose rows that move its pitch while it sounds.

    Attributes:
        place: Where the note-on stands in the song.
        voice_id: The voice the note sounds.
        transpose: The transpose the note starts at, which is zero where its row states none.
        repitches: The transpose rows that reach the note, in the order the song plays them.
    """

    place: RowPlace
    voice_id: str
    transpose: int
    repitches: Tuple[Repitch, ...]


@dataclass
class _OpenNote:
    """The note a walk is following, gathering the rows that reach it until another row ends it."""

    place: RowPlace
    voice_id: str
    transpose: int
    rows: int = field(default=NO_ROWS)
    repitches: List[Repitch] = field(default_factory=list)

    def closed(self) -> SoundingNote:
        return SoundingNote(
            place=self.place,
            voice_id=self.voice_id,
            transpose=self.transpose,
            repitches=tuple(self.repitches),
        )


@dataclass
class _NoteWalk:
    """One channel's pass through the song, following the note it sounds from row to row."""

    channel_name: ChannelName
    instruments: Container[Tuple[str, ChannelName]]
    notes: List[SoundingNote] = field(default_factory=list)
    sounding: Optional[_OpenNote] = field(default=None)

    def read(self, row: Row, place: RowPlace) -> None:
        """Moves the walk onto one row, the way the song's own walk applies it."""
        match row.command:
            case NoteOn() as note_on:
                self._close()
                if (note_on.voice_id, self.channel_name) in self.instruments:
                    self.sounding = _OpenNote(
                        place=place,
                        voice_id=note_on.voice_id,
                        transpose=row.transpose if row.transpose is not None else NOTE_TRANSPOSE,
                    )
            case NoteOff():
                self._close()
            case None:
                if row.transpose is not None and self.sounding is not None:
                    self.sounding.repitches.append(
                        Repitch(
                            place=place,
                            transpose=row.transpose,
                            rows=self.sounding.rows,
                        )
                    )

    def pass_row(self) -> None:
        """Counts one more row the sounding note has played through."""
        if self.sounding is not None:
            self.sounding.rows += 1

    def finish(self) -> Tuple[SoundingNote, ...]:
        """The notes the pass found a transpose row reaching."""
        self._close()
        return tuple(self.notes)

    def _close(self) -> None:
        if self.sounding is not None and self.sounding.repitches:
            self.notes.append(self.sounding.closed())

        self.sounding = None


def sounding_notes(
    song: Song,
    channel_name: ChannelName,
    instruments: Container[Tuple[str, ChannelName]],
) -> Tuple[SoundingNote, ...]:
    """Walks one channel through the order once, gathering the notes that transpose rows move.

    The song's walk plays the order frame by frame, and a row naming no note leaves the voice
    playing, so a row stating a transpose moves the note already sounding. A note-on or a note-off
    ends the note, and so does a note-on naming a voice with no instrument on the channel, which the
    export writes as a note cut. A frame leaving the channel empty plays on with the
    note it carries, so a note's rows are counted across frames. A transpose row reached while no
    note sounds moves nothing.

    Args:
        song: The arrangement being exported.
        channel_name: The channel whose rows are walked.
        instruments: The ``(voice id, channel)`` pairs the export holds an instrument for.

    Returns:
        Tuple[SoundingNote, ...]: The notes at least one transpose row reaches, in the order the
            song plays them.
    """
    walk = _NoteWalk(channel_name=channel_name, instruments=instruments)
    for order_position, frame in enumerate(song.order):
        pattern_index = frame.get(channel_name)
        pattern = song.pattern(channel_name, pattern_index) if pattern_index is not None else None
        for row_index in range(song.rows_per_pattern):
            if pattern_index is not None and pattern is not None and row_index < len(pattern.rows):
                walk.read(
                    pattern.rows[row_index],
                    RowPlace(
                        order_position=order_position,
                        pattern_index=pattern_index,
                        row_index=row_index,
                    ),
                )

            walk.pass_row()

    return walk.finish()
