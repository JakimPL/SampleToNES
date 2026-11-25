from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_tools.calibration.corpus import midi
from sampletones_tools.calibration.corpus.midi import MidiFormatError, Note, read_midi
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from ..midifiles import (
    SECONDS_PER_TICK,
    TEMPO,
    TICKS_PER_BEAT,
    Message,
    midi_file,
    nesmdb_piece,
    ticks,
    track,
)

NOTE_ON: Final[int] = 0x90
NOTE_OFF: Final[int] = 0x80
CONTROL_CHANGE: Final[int] = 0xB0
PROGRAM_CHANGE: Final[int] = 0xC0
VOLUME: Final[int] = 11
A4: Final[int] = 69
VELOCITY: Final[int] = 10
SMPTE_DIVISION: Final[int] = 0xE728
DIVISION_START: Final[int] = 12
DIVISION_END: Final[int] = 14
PLAYED: Final[bytes] = midi_file([track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (1, bytes([NOTE_OFF, A4, 0]))])])
NESMDB_TICKS_PER_SECOND: Final[int] = 44_100
FOUR_MINUTES: Final[int] = 240


def _set_tempo(microseconds_per_beat: int) -> bytes:
    return b"\xff\x51\x03" + microseconds_per_beat.to_bytes(3, "big")


def _notes(messages: Tuple[Message, ...]) -> List[Note]:
    """Every note a one-track file of ``messages`` plays."""
    return [note for played in read_midi(midi_file([track("p1", messages)])).values() for note in played.notes]


class TestReadMidi:
    def test_every_named_track_is_read_with_its_notes_in_seconds(self) -> None:
        tracks = read_midi(nesmdb_piece())

        assert list(tracks) == ["p1", "tr", "no"]
        (note,) = tracks["p1"].notes
        assert (note.start, note.pitch, note.velocity) == (0.0, 69, 12)
        assert note.end == pytest.approx(ticks(1.0) * SECONDS_PER_TICK)

    def test_a_note_on_of_no_velocity_ends_the_note(self) -> None:
        (note,) = read_midi(nesmdb_piece())["tr"].notes

        assert note.end == pytest.approx(1.0, abs=SECONDS_PER_TICK)

    def test_every_controller_keeps_its_values_over_time(self) -> None:
        controllers = read_midi(nesmdb_piece())["p1"].controllers

        assert controllers[12] == [(0.0, 1)]
        assert controllers[11] == [(pytest.approx(0.5, abs=SECONDS_PER_TICK), 6)]

    def test_notes_are_ordered_by_their_start(self) -> None:
        messages = (
            (0, bytes([NOTE_ON, A4, VELOCITY])),
            (ticks(0.25), bytes([NOTE_ON, A4 + 2, VELOCITY])),
            (ticks(0.25), bytes([NOTE_OFF, A4 + 2, 0])),
            (ticks(0.25), bytes([NOTE_OFF, A4, 0])),
        )

        assert [note.pitch for note in _notes(messages)] == [A4, A4 + 2]

    def test_a_track_playing_no_note_is_left_out(self) -> None:
        pulse = track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (ticks(0.5), bytes([NOTE_OFF, A4, 0]))])
        silent = track("p2", [(0, bytes([CONTROL_CHANGE, VOLUME, 4]))])

        assert list(read_midi(midi_file([pulse, silent]))) == ["p1"]


class TestPrograms(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        messages: Tuple[Message, ...]
        pitches: Tuple[int, ...]

    test_cases = (
        TestCase(
            messages=(
                (0, bytes([CONTROL_CHANGE, VOLUME, 4])),
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.25), bytes([NOTE_OFF, A4, 0])),
                (0, bytes([PROGRAM_CHANGE, 5])),
                (0, bytes([CONTROL_CHANGE, VOLUME, 6])),
                (0, bytes([NOTE_ON, A4 + 2, VELOCITY])),
                (ticks(0.25), bytes([NOTE_OFF, A4 + 2, 0])),
            ),
            pitches=(A4, A4 + 2),
            expected=((0.0, 4), (0.25, 6)),
            label="a change set before the first note",
        ),
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.25), bytes([NOTE_OFF, A4, 0])),
                (0, bytes([PROGRAM_CHANGE, 5])),
                (0, bytes([CONTROL_CHANGE, VOLUME, 6])),
                (0, bytes([NOTE_ON, A4 + 2, VELOCITY])),
                (ticks(0.25), bytes([NOTE_OFF, A4 + 2, 0])),
                (0, bytes([PROGRAM_CHANGE, 0])),
                (0, bytes([CONTROL_CHANGE, VOLUME, 4])),
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.25), bytes([NOTE_OFF, A4, 0])),
            ),
            pitches=(A4, A4 + 2, A4),
            expected=((0.25, 6), (0.5, 4)),
            label="a return to the first program",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_track_playing_two_programs_is_read_whole(self, test_case: TestCase) -> None:
        pulse = read_midi(midi_file([track("p1", test_case.messages)]))["p1"]

        assert [note.pitch for note in pulse.notes] == list(test_case.pitches)
        assert pulse.controllers[VOLUME] == [
            (pytest.approx(time, abs=SECONDS_PER_TICK), value) for time, value in test_case.expected
        ]


class TestMalformedFiles(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        data: bytes

    test_cases = (
        TestCase(data=b"RIFF", label="no header"),
        TestCase(data=PLAYED[:-3], label="a track cut short"),
        TestCase(data=PLAYED[:DIVISION_END] + b"MRIF" + PLAYED[DIVISION_END + 4 :], label="a track of another kind"),
        TestCase(data=midi_file([]), label="no track"),
        TestCase(
            data=PLAYED.replace(bytes([NOTE_ON, A4]), bytes([NOTE_ON, 0x80 | A4])), label="a data byte out of range"
        ),
        TestCase(data=PLAYED.replace(b"\xff\x03\x02p1", b"\xff\x51\x02\x07\xa1"), label="a tempo cut short"),
        TestCase(data=PLAYED[:DIVISION_START] + bytes(2) + PLAYED[DIVISION_END:], label="no ticks a beat"),
        TestCase(data=PLAYED.replace(b"\xff\x03\x02p1", b"\xff\x59\x02\x50\x00"), label="a key signature of no key"),
        TestCase(
            data=PLAYED[:DIVISION_START] + SMPTE_DIVISION.to_bytes(2, "big") + PLAYED[DIVISION_END:],
            label="time in SMPTE frames",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_bytes_holding_no_midi_file_are_refused(self, test_case: TestCase) -> None:
        with pytest.raises(MidiFormatError, match="reads no MIDI file"):
            read_midi(test_case.data)


class TestLength:
    def test_a_piece_four_minutes_long_at_nesmdb_s_clock_reads(self) -> None:
        length = FOUR_MINUTES * NESMDB_TICKS_PER_SECOND
        messages = ((0, bytes([NOTE_ON, A4, VELOCITY])), (length, bytes([NOTE_OFF, A4, 0])))

        (note,) = _notes(messages)

        assert note.end == pytest.approx(length * SECONDS_PER_TICK)

    def test_a_file_spanning_as_many_ticks_as_the_limit_reads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(midi, "LONGEST_FILE_TICKS", TICKS_PER_BEAT)
        messages = ((0, bytes([NOTE_ON, A4, VELOCITY])), (TICKS_PER_BEAT - 1, bytes([NOTE_OFF, A4, 0])))

        assert _notes(messages)

    def test_a_file_spanning_more_ticks_than_the_limit_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(midi, "LONGEST_FILE_TICKS", TICKS_PER_BEAT)
        messages = ((0, bytes([NOTE_ON, A4, VELOCITY])), (TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0])))

        with pytest.raises(MidiFormatError, match="likely corrupt"):
            _notes(messages)


class TestStrikingAgain(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        messages: Tuple[Message, ...]

    test_cases = (
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.5), bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
            ),
            expected=((0.0, 1.0), (0.5, 1.0)),
            label="struck again while it sounds",
        ),
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
            ),
            expected=((0.0, 0.5), (0.5, 1.0)),
            label="released, then struck at one tick",
        ),
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4, VELOCITY])),
                (ticks(0.5), bytes([NOTE_ON, A4, VELOCITY])),
                (0, bytes([NOTE_OFF, A4, 0])),
                (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
            ),
            expected=((0.0, 0.5), (0.5, 1.0)),
            label="struck, then released at one tick",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_release_ends_the_strikes_of_its_pitch_before_its_tick(self, test_case: TestCase) -> None:
        assert [(note.start, note.end) for note in _notes(test_case.messages)] == [
            pytest.approx(span, abs=SECONDS_PER_TICK) for span in test_case.expected
        ]


class TestNotesLeftOut(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        messages: Tuple[Message, ...]

    test_cases = (
        TestCase(
            messages=((0, bytes([NOTE_ON, A4, VELOCITY])), (0, bytes([NOTE_OFF, A4, 0]))),
            expected=(),
            label="released at its strike on the first tick",
        ),
        TestCase(
            messages=((ticks(0.5), bytes([NOTE_ON, A4, VELOCITY])), (0, bytes([NOTE_OFF, A4, 0]))),
            expected=(),
            label="released at its strike on a later tick",
        ),
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4 + 2, VELOCITY])),
                (ticks(0.5), bytes([NOTE_ON, A4, VELOCITY])),
                (0, bytes([NOTE_OFF, A4 + 2, 0])),
                (0, bytes([NOTE_OFF, A4, 0])),
            ),
            expected=((A4 + 2, 0.0, 0.5),),
            label="released at its strike where another pitch is released",
        ),
        TestCase(
            messages=(
                (0, bytes([NOTE_ON, A4 + 2, VELOCITY])),
                (ticks(0.5), bytes([NOTE_OFF, A4 + 2, 0])),
                (0, bytes([NOTE_ON, A4, VELOCITY])),
            ),
            expected=((A4 + 2, 0.0, 0.5),),
            label="never released",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_note_released_at_its_strike_or_never_is_left_out(self, test_case: TestCase) -> None:
        assert [(note.pitch, note.start, note.end) for note in _notes(test_case.messages)] == [
            (pitch, pytest.approx(start, abs=SECONDS_PER_TICK), pytest.approx(end, abs=SECONDS_PER_TICK))
            for pitch, start, end in test_case.expected
        ]


class TestTempoMap(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        beat: int
        first: int
        last: int

    test_cases = (
        TestCase(beat=0, first=TEMPO // 2, last=2 * TEMPO, label="faster first, at the start"),
        TestCase(beat=0, first=2 * TEMPO, last=TEMPO // 2, label="slower first, at the start"),
        TestCase(beat=1, first=TEMPO // 2, last=2 * TEMPO, label="faster first, a beat in"),
        TestCase(beat=1, first=2 * TEMPO, last=TEMPO // 2, label="slower first, a beat in"),
    )

    def test_a_piece_setting_no_tempo_plays_at_the_default(self) -> None:
        messages = ((0, bytes([NOTE_ON, A4, VELOCITY])), (TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0])))

        (note,) = _notes(messages)

        assert note.end == pytest.approx(TEMPO / 1e6)

    def test_a_tempo_the_first_track_sets_times_every_track_from_its_tick_on(self) -> None:
        conductor = track("conductor", [(TICKS_PER_BEAT, _set_tempo(TEMPO // 2))], tempo=True)
        pulse = track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (2 * TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0]))])

        (note,) = read_midi(midi_file([conductor, pulse]))["p1"].notes

        assert note.end == pytest.approx(TEMPO / 1e6 + TEMPO / 2 / 1e6)

    @pytest.mark.filterwarnings("ignore:Tempo, Key or Time signature change events found on non-zero tracks")
    def test_a_tempo_a_later_track_sets_is_left_out(self) -> None:
        pulse = track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (2 * TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0]))])
        conductor = track("conductor", [(TICKS_PER_BEAT, _set_tempo(TEMPO // 2))])

        (note,) = read_midi(midi_file([pulse, conductor]))["p1"].notes

        assert note.end == pytest.approx(2 * TEMPO / 1e6)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_of_two_tempos_set_at_one_tick_the_one_the_file_sets_last_holds(self, test_case: TestCase) -> None:
        tempos = [(test_case.beat * TICKS_PER_BEAT, _set_tempo(test_case.first)), (0, _set_tempo(test_case.last))]
        conductor = track("conductor", tempos)
        pulse = track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (2 * TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0]))])

        (note,) = read_midi(midi_file([conductor, pulse]))["p1"].notes

        assert note.end == pytest.approx((test_case.beat * TEMPO + (2 - test_case.beat) * test_case.last) / 1e6)
