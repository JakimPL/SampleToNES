import pytest

from sampletones_tools.calibration.corpus.midi import MidiFormatError, read_midi

from ..midifiles import SECONDS_PER_TICK, nesmdb_piece, ticks


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
