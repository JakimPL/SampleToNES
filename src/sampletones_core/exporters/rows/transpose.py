from __future__ import annotations

from dataclasses import dataclass, field
from typing import Container, Dict, Final, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.levels import RowPlace
from sampletones_core.performance.rows import apply_row, note_step
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import VoiceLookup

NO_ROWS: Final[int] = 0

PatternCell = Tuple[int, int]


@dataclass(frozen=True)
class Repitch:
    """A row stating a pitch and no note, which moves the note sounding on its channel.

    The song keeps the voice where it stands, so the note goes on from the tick it reached, and every
    tick from this row on sounds at the step the row reaches.

    Attributes:
        place: Where the row stands in the song.
        step: The step the row moves the note to, measured from the voice's reference like a
            note-on's.
        rows: How many rows the note has sounded for when this row begins, counted across frames.
    """

    place: RowPlace
    step: int
    rows: int


@dataclass(frozen=True)
class NoteStart:
    """What a note-on the order reaches started, as the song's walk played it.

    Attributes:
        voice_id: The voice the note-on names.
        step: The step the voice started at, measured from its reference, or ``None`` where the
            row started nothing.
    """

    voice_id: str
    step: Optional[int]


@dataclass(frozen=True)
class SoundingNote:
    """A note-on the song sounds, with the pitch rows that move it while it sounds.

    Attributes:
        place: Where the note-on stands in the song.
        voice_id: The voice the note sounds.
        step: The step the note starts at, measured from the voice's reference.
        repitches: The pitch rows that reach the note, in the order the song plays them.
    """

    place: RowPlace
    voice_id: str
    step: int
    repitches: Tuple[Repitch, ...]


@dataclass
class _OpenNote:
    """The note a walk is following, gathering the rows that reach it until another row ends it."""

    place: RowPlace
    voice_id: str
    step: int
    rows: int = field(default=NO_ROWS)
    repitches: List[Repitch] = field(default_factory=list)

    def closed(self) -> SoundingNote:
        return SoundingNote(
            place=self.place,
            voice_id=self.voice_id,
            step=self.step,
            repitches=tuple(self.repitches),
        )


@dataclass
class _NoteFollower:
    """One channel's pass through the song, following the note the channel sounds from row to row."""

    channel_name: ChannelName
    instruments: Container[Tuple[str, ChannelName]]
    starts: Dict[RowPlace, NoteStart] = field(default_factory=dict)
    notes: List[SoundingNote] = field(default_factory=list)
    sounding: Optional[_OpenNote] = field(default=None)

    def read(
        self,
        row: Row,
        place: RowPlace,
        performance: ChannelPerformance,
        restarted: bool,
    ) -> None:
        """Reads what the song's walk made of one row, once the channel has been moved onto it."""
        match row.command:
            case NoteOn() as note_on:
                self._close()
                if (note_on.voice_id, self.channel_name) not in self.instruments:
                    return

                if not restarted:
                    self.starts[place] = NoteStart(voice_id=note_on.voice_id, step=None)
                    return

                self.starts[place] = NoteStart(voice_id=note_on.voice_id, step=performance.transpose)
                self.sounding = _OpenNote(
                    place=place,
                    voice_id=note_on.voice_id,
                    step=performance.transpose,
                )
            case NoteOff():
                self._close()
            case None:
                if row.pitch is not None and self.sounding is not None:
                    self.sounding.repitches.append(
                        Repitch(
                            place=place,
                            step=performance.transpose,
                            rows=self.sounding.rows,
                        )
                    )

    def pass_row(self) -> None:
        """Counts one more row the sounding note has played through."""
        if self.sounding is not None:
            self.sounding.rows += 1

    def finish(self) -> Tuple[SoundingNote, ...]:
        """The notes the pass found a pitch row reaching."""
        self._close()
        return tuple(self.notes)

    def _close(self) -> None:
        if self.sounding is not None and self.sounding.repitches:
            self.notes.append(self.sounding.closed())

        self.sounding = None


@dataclass(frozen=True)
class PitchWalk:
    """One channel's pass through the song as playback makes it, read for what an export writes.

    The walk moves a channel through the order the way the song's own walk does, row by row through
    :func:`apply_row`, so the step every note starts at and the step every pitch row reaches are the
    ones the song sounds: an instrument placed without a pitch starts on the pitch the channel was
    sounding, and one placed on a silent channel starts nothing. A note-on naming a voice the export
    has no instrument for on the channel is written as a note cut, so the walk follows no note from
    it. A frame leaving the channel empty plays on with the note it carries, so a note's rows are
    counted across frames.

    Attributes:
        starts: Per note-on the order reaches and the export has an instrument for, what it
            started, in the order the song plays them.
        notes: The notes at least one pitch row moves, in the order the song plays them.
    """

    starts: Dict[RowPlace, NoteStart]
    notes: Tuple[SoundingNote, ...]

    @classmethod
    def walk(
        cls,
        song: Song,
        channel_name: ChannelName,
        instruments: Container[Tuple[str, ChannelName]],
        voices: VoiceLookup,
    ) -> PitchWalk:
        """Walks one channel through the order once.

        Args:
            song: The arrangement being exported.
            channel_name: The channel whose rows are walked.
            instruments: The ``(voice id, channel)`` pairs the export holds an instrument for.
            voices: Where a voice id resolves to the voice it names.

        Returns:
            PitchWalk: What every note-on started at, and the notes pitch rows move.
        """
        performance = ChannelPerformance()
        follower = _NoteFollower(channel_name=channel_name, instruments=instruments)
        for order_position, frame in enumerate(song.order):
            pattern_index = frame.get(channel_name)
            pattern = song.pattern(channel_name, pattern_index) if pattern_index is not None else None
            for row_index in range(song.rows_per_pattern):
                if pattern_index is not None and pattern is not None and row_index < len(pattern.rows):
                    row = pattern.rows[row_index]
                    place = RowPlace(
                        order_position=order_position,
                        pattern_index=pattern_index,
                        row_index=row_index,
                    )
                    restarted = apply_row(performance, row, channel_name, voices)
                    follower.read(row, place, performance, restarted)

                follower.pass_row()

        return cls(starts=dict(follower.starts), notes=follower.finish())

    def frame_starts(self, order_position: int) -> Dict[int, Optional[int]]:
        """The step each note-on of one frame starts at, keyed by row."""
        return {
            place.row_index: start.step
            for place, start in self.starts.items()
            if place.order_position == order_position
        }


def unreached_start(
    row: Row,
    channel_name: ChannelName,
    voices: VoiceLookup,
) -> Optional[int]:
    """The step a note-on the order never reaches would start at, on a channel sounding nothing.

    A format writing every pattern the pool holds reaches rows the song never plays, and writes
    them as the song would play them from silence.

    Args:
        row: The row holding the note-on.
        channel_name: The channel the row stands on.
        voices: Where a voice id resolves to the voice it names.

    Returns:
        Optional[int]: The step from the voice's reference, or ``None`` where the row starts
            nothing or names a voice the project lacks.
    """
    if not isinstance(row.command, NoteOn):
        return None

    voice = voices(row.command.voice_id)
    if voice is None:
        return None

    return note_step(row.pitch, voice, channel_name, sounding=None)
