from typing import Dict, Final, FrozenSet, List, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.exporters.rows.levels import RowPlace
from sampletones_core.exporters.rows.transpose import (
    NoteStart,
    PitchWalk,
    Repitch,
    SoundingNote,
    unreached_start,
)
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Note, RowPitch, Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import VoiceLookup, VoiceUnion, voice_reference
from tests.suite.performance import make_pulse_reconstruction

ROWS_PER_PATTERN: Final[int] = 4
CHANNEL: Final[ChannelName] = ChannelName.PULSE1
REFERENCE: Final[int] = 60
NOTE_ON_STEP: Final[int] = 5
RAISED: Final[int] = 2
LOWERED: Final[int] = -3
TYPED_NOTE: Final[int] = 67
BENT_NOTE: Final[int] = 65
GONE: Final[str] = "gone"

SAMPLE: Final[Sample] = Sample(name="voice", reconstruction=make_pulse_reconstruction(pitch=REFERENCE))
SILENT: Final[Sample] = Sample(name="silent", reconstruction=make_pulse_reconstruction(pitch=REFERENCE))
LEAD: Final[Instrument] = Instrument(
    name="lead",
    envelopes=InstrumentEnvelopes(volume=Envelope(items=(MAX_VOLUME,))),
    initial_pitch=REFERENCE,
)
VOICE: Final[str] = SAMPLE.id
SILENT_VOICE: Final[str] = SILENT.id
VOICES: Final[Dict[str, VoiceUnion]] = {voice.id: voice for voice in (SAMPLE, SILENT, LEAD)}
LOOKUP: Final[VoiceLookup] = VOICES.get
INSTRUMENTS: Final[FrozenSet[Tuple[str, ChannelName]]] = frozenset({(VOICE, CHANNEL), (LEAD.id, CHANNEL)})


def _song(
    patterns: Dict[int, List[Row]],
    order: List[Optional[int]],
) -> Song:
    """A song of one channel's patterns, every other channel left empty."""
    pools = {
        channel_name: Channel(
            name=channel_name,
            patterns=(
                {index: Pattern(rows=rows) for index, rows in patterns.items()} if channel_name == CHANNEL else {}
            ),
        )
        for channel_name in ChannelName.items()
    }
    return Song(
        rows_per_pattern=ROWS_PER_PATTERN,
        order=[{CHANNEL: index} for index in order],
        channels=pools,
    )


def _rows(*cells: Tuple[int, Row]) -> List[Row]:
    rows = [Row() for _ in range(ROWS_PER_PATTERN)]
    for row_index, row in cells:
        rows[row_index] = row

    return rows


def _place(order_position: int, pattern_index: int, row_index: int) -> RowPlace:
    return RowPlace(order_position=order_position, pattern_index=pattern_index, row_index=row_index)


def _note(pitch: Optional[RowPitch] = None, voice_id: str = VOICE) -> Row:
    return Row(command=NoteOn(voice_id=voice_id), pitch=pitch)


def _walk(song: Song) -> PitchWalk:
    return PitchWalk.walk(song, CHANNEL, INSTRUMENTS, LOOKUP)


def _started(step: Optional[int], voice_id: str = VOICE) -> NoteStart:
    return NoteStart(voice_id=voice_id, step=step)


def _step_to(note: int, voice: VoiceUnion = SAMPLE) -> int:
    return note - voice_reference(voice, CHANNEL)


class TestWhatEveryNoteOnStartsAt:
    """The walk starts every note the way playback does, so the step it records is the one the song sounds."""

    def test_a_step_starts_at_itself(self) -> None:
        walk = _walk(_song({0: _rows((0, _note(Step(value=NOTE_ON_STEP))))}, [0]))

        assert walk.starts == {_place(0, 0, 0): _started(NOTE_ON_STEP)}

    def test_a_note_starts_at_the_step_reaching_it(self) -> None:
        walk = _walk(_song({0: _rows((0, _note(Note(value=TYPED_NOTE))))}, [0]))

        assert walk.starts == {_place(0, 0, 0): _started(_step_to(TYPED_NOTE))}

    def test_a_sample_stating_no_pitch_starts_as_recorded_whatever_sounded_before(self) -> None:
        walk = _walk(_song({0: _rows((0, _note(Note(value=TYPED_NOTE))), (2, _note()))}, [0]))

        assert walk.starts[_place(0, 0, 2)] == _started(0)

    def test_an_instrument_stating_no_pitch_starts_at_the_pitch_the_sample_was_sounding(self) -> None:
        walk = _walk(_song({0: _rows((0, _note(Note(value=TYPED_NOTE))), (2, _note(voice_id=LEAD.id)))}, [0]))

        assert walk.starts[_place(0, 0, 2)] == _started(_step_to(TYPED_NOTE, LEAD), LEAD.id)

    def test_the_pitch_an_instrument_goes_on_from_follows_a_bend(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(pitch=Note(value=BENT_NOTE))), (2, _note(voice_id=LEAD.id)))}, [0])

        walk = _walk(song)

        assert walk.starts[_place(0, 0, 2)] == _started(_step_to(BENT_NOTE, LEAD), LEAD.id)

    def test_an_instrument_stating_no_pitch_after_a_note_off_starts_nothing(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(command=NoteOff())), (2, _note(voice_id=LEAD.id)))}, [0])

        walk = _walk(song)

        assert walk.starts[_place(0, 0, 2)] == _started(None, LEAD.id)

    def test_an_instrument_stating_no_pitch_on_a_fresh_channel_starts_nothing(self) -> None:
        walk = _walk(_song({0: _rows((0, _note(voice_id=LEAD.id)))}, [0]))

        assert walk.starts == {_place(0, 0, 0): _started(None, LEAD.id)}

    def test_the_pitch_an_instrument_goes_on_from_crosses_frames(self) -> None:
        song = _song({0: _rows((0, _note(Step(value=NOTE_ON_STEP)))), 1: _rows((0, _note(voice_id=LEAD.id)))}, [0, 1])

        walk = _walk(song)

        assert walk.starts[_place(1, 1, 0)] == _started(NOTE_ON_STEP, LEAD.id)

    def test_a_pattern_two_frames_play_after_different_pitches_starts_differently_in_each(self) -> None:
        song = _song(
            {
                0: _rows((0, _note(Step(value=RAISED)))),
                1: _rows((0, _note(Step(value=LOWERED)))),
                2: _rows((0, _note(voice_id=LEAD.id))),
            },
            [0, 2, 1, 2],
        )

        walk = _walk(song)

        assert walk.starts[_place(1, 2, 0)] == _started(RAISED, LEAD.id)
        assert walk.starts[_place(3, 2, 0)] == _started(LOWERED, LEAD.id)

    def test_a_voice_without_an_instrument_on_the_channel_records_no_start_and_sounds_on(self) -> None:
        """The export writes a note cut for it, while the song goes on sounding it."""
        song = _song(
            {0: _rows((0, _note(Note(value=TYPED_NOTE), voice_id=SILENT_VOICE)), (2, _note(voice_id=LEAD.id)))}, [0]
        )

        walk = _walk(song)

        assert walk.starts == {_place(0, 0, 2): _started(_step_to(TYPED_NOTE, LEAD), LEAD.id)}

    def test_a_voice_the_project_lacks_leaves_a_silent_channel(self) -> None:
        song = _song(
            {0: _rows((0, _note(Note(value=TYPED_NOTE))), (1, _note(voice_id=GONE)), (2, _note(voice_id=LEAD.id)))}, [0]
        )

        walk = _walk(song)

        assert walk.starts == {
            _place(0, 0, 0): _started(_step_to(TYPED_NOTE)),
            _place(0, 0, 2): _started(None, LEAD.id),
        }

    def test_the_starts_of_one_frame_are_read_by_row(self) -> None:
        song = _song({0: _rows((0, _note(Step(value=RAISED))), (2, _note(Step(value=LOWERED))))}, [0, 0])

        walk = _walk(song)

        assert walk.frame_starts(1) == {0: RAISED, 2: LOWERED}


class TestARowTheOrderNeverReaches:
    """A pattern the order never plays is written as the song would play it from silence."""

    def test_a_sample_starts_as_recorded(self) -> None:
        assert unreached_start(_note(), CHANNEL, LOOKUP) == 0

    def test_a_pitch_starts_at_the_step_reaching_it(self) -> None:
        assert unreached_start(_note(Note(value=TYPED_NOTE), voice_id=LEAD.id), CHANNEL, LOOKUP) == _step_to(
            TYPED_NOTE, LEAD
        )

    def test_an_instrument_stating_no_pitch_starts_nothing(self) -> None:
        assert unreached_start(_note(voice_id=LEAD.id), CHANNEL, LOOKUP) is None

    def test_a_row_naming_no_note_starts_nothing(self) -> None:
        assert unreached_start(Row(pitch=Step(value=RAISED)), CHANNEL, LOOKUP) is None

    def test_a_voice_the_project_lacks_starts_nothing(self) -> None:
        assert unreached_start(_note(voice_id=GONE), CHANNEL, LOOKUP) is None


class TestTheNotesAPitchRowMoves:
    """A row stating a pitch and no note moves the note already sounding, which keeps playing
    from the tick it reached, so the walk names each such row beside the note it moves and how long
    that note has sounded.
    """

    def test_a_pitch_row_is_named_beside_the_note_it_moves(self) -> None:
        song = _song({0: _rows((0, _note()), (2, Row(pitch=Step(value=RAISED))))}, [0])

        assert _walk(song).notes == (
            SoundingNote(
                place=_place(0, 0, 0),
                voice_id=VOICE,
                step=0,
                repitches=(Repitch(place=_place(0, 0, 2), step=RAISED, rows=2),),
            ),
        )

    def test_a_note_bend_is_a_repitch_at_the_step_reaching_it(self) -> None:
        song = _song({0: _rows((0, _note()), (2, Row(pitch=Note(value=BENT_NOTE))))}, [0])

        (note,) = _walk(song).notes

        assert note.repitches == (Repitch(place=_place(0, 0, 2), step=_step_to(BENT_NOTE), rows=2),)

    def test_the_note_keeps_the_step_it_started_at(self) -> None:
        song = _song({0: _rows((0, _note(Step(value=NOTE_ON_STEP))), (1, Row(pitch=Step(value=RAISED))))}, [0])

        (note,) = _walk(song).notes

        assert note.step == NOTE_ON_STEP

    def test_every_pitch_row_reaching_the_note_is_counted_from_it(self) -> None:
        song = _song(
            {0: _rows((0, _note()), (1, Row(pitch=Step(value=RAISED))), (3, Row(pitch=Step(value=LOWERED))))}, [0]
        )

        (note,) = _walk(song).notes

        assert [(repitch.step, repitch.rows) for repitch in note.repitches] == [(RAISED, 1), (LOWERED, 3)]

    def test_rows_are_counted_across_frames(self) -> None:
        song = _song({0: _rows((1, _note())), 1: _rows((2, Row(pitch=Step(value=RAISED))))}, [0, 1])

        (note,) = _walk(song).notes

        assert note.repitches == (Repitch(place=_place(1, 1, 2), step=RAISED, rows=5),)

    def test_an_empty_frame_keeps_the_note_sounding(self) -> None:
        song = _song({0: _rows((0, _note())), 1: _rows((1, Row(pitch=Step(value=RAISED))))}, [0, None, 1])

        (note,) = _walk(song).notes

        assert note.repitches[0].rows == 2 * ROWS_PER_PATTERN + 1

    def test_a_pattern_played_twice_is_reached_in_each_frame(self) -> None:
        song = _song({0: _rows((0, _note()), (2, Row(pitch=Step(value=RAISED))))}, [0, 0])

        notes = _walk(song).notes

        assert [note.place.order_position for note in notes] == [0, 1]

    def test_a_note_off_ends_the_note(self) -> None:
        song = _song({0: _rows((0, _note()), (1, Row(command=NoteOff())), (2, Row(pitch=Step(value=RAISED))))}, [0])

        assert _walk(song).notes == ()

    def test_a_voice_without_an_instrument_on_the_channel_sounds_no_note(self) -> None:
        song = _song({0: _rows((0, _note(voice_id=SILENT_VOICE)), (2, Row(pitch=Step(value=RAISED))))}, [0])

        assert _walk(song).notes == ()

    def test_a_pitch_row_before_any_note_moves_nothing(self) -> None:
        song = _song({0: _rows((0, Row(pitch=Step(value=RAISED))), (2, _note()))}, [0])

        assert _walk(song).notes == ()

    def test_a_note_no_pitch_row_reaches_is_in_the_starts_and_out_of_the_notes(self) -> None:
        song = _song(
            {0: _rows((0, _note()), (1, Row(volume=RAISED)), (2, _note()), (3, Row(pitch=Step(value=RAISED))))}, [0]
        )

        walk = _walk(song)

        assert set(walk.starts) == {_place(0, 0, 0), _place(0, 0, 2)}
        assert [note.place.row_index for note in walk.notes] == [2]
