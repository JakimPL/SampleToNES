from typing import Final

import pytest

from sampletones_tools.calibration.corpus.midi import MidiFormatError, read_midi

from ..midifiles import SECONDS_PER_TICK, TEMPO, TICKS_PER_BEAT, midi_file, nesmdb_piece, ticks, track

NOTE_ON: Final[int] = 0x90
NOTE_OFF: Final[int] = 0x80
PROGRAM_CHANGE: Final[int] = 0xC0
A4: Final[int] = 69
VELOCITY: Final[int] = 10
SMPTE_DIVISION: Final[int] = 0xE728


def _set_tempo(microseconds_per_beat: int) -> bytes:
    return b"\xff\x51\x03" + microseconds_per_beat.to_bytes(3, "big")


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

    def test_bytes_without_a_header_are_refused(self) -> None:
        with pytest.raises(MidiFormatError, match="no MIDI header"):
            read_midi(b"RIFF")

    def test_time_in_smpte_frames_is_refused(self) -> None:
        header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big") + (0).to_bytes(2, "big")

        with pytest.raises(MidiFormatError, match="SMPTE"):
            read_midi(header + SMPTE_DIVISION.to_bytes(2, "big"))


class TestEvents:
    def test_a_message_without_a_status_byte_takes_the_one_before(self) -> None:
        piece = midi_file([track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (ticks(0.5), bytes([A4, 0]))])])

        (note,) = read_midi(piece)["p1"].notes

        assert note.end == pytest.approx(0.5, abs=SECONDS_PER_TICK)

    def test_system_exclusive_and_one_byte_messages_are_stepped_over(self) -> None:
        messages = [
            (0, b"\xf0\x03\x01\x02\xf7"),
            (0, bytes([PROGRAM_CHANGE, 5])),
            (0, bytes([NOTE_ON, A4, VELOCITY])),
            (ticks(0.5), bytes([NOTE_OFF, A4, 0])),
        ]

        (note,) = read_midi(midi_file([track("p1", messages)]))["p1"].notes

        assert (note.pitch, note.velocity) == (A4, VELOCITY)
        assert note.end == pytest.approx(0.5, abs=SECONDS_PER_TICK)

    def test_notes_are_ordered_by_their_start(self) -> None:
        messages = [
            (0, bytes([NOTE_ON, A4, VELOCITY])),
            (ticks(0.25), bytes([NOTE_ON, A4 + 2, VELOCITY])),
            (ticks(0.25), bytes([NOTE_OFF, A4 + 2, 0])),
            (ticks(0.25), bytes([NOTE_OFF, A4, 0])),
        ]

        notes = read_midi(midi_file([track("p1", messages)]))["p1"].notes

        assert [note.pitch for note in notes] == [A4, A4 + 2]


class TestTempoMap:
    def test_a_piece_setting_no_tempo_plays_at_the_default(self) -> None:
        piece = midi_file(
            [track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0]))])]
        )

        (note,) = read_midi(piece)["p1"].notes

        assert note.end == pytest.approx(TEMPO / 1e6)

    def test_a_tempo_set_in_one_track_times_every_track_from_its_tick_on(self) -> None:
        conductor = track("conductor", [(TICKS_PER_BEAT, _set_tempo(TEMPO // 2))], tempo=True)
        pulse = track("p1", [(0, bytes([NOTE_ON, A4, VELOCITY])), (2 * TICKS_PER_BEAT, bytes([NOTE_OFF, A4, 0]))])

        (note,) = read_midi(midi_file([conductor, pulse]))["p1"].notes

        assert note.end == pytest.approx(TEMPO / 1e6 + TEMPO / 2 / 1e6)
