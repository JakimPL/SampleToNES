from typing import Final

import pytest

from sampletones_application.utils.midi import (
    MidiAllNotesOff,
    MidiNoteOff,
    MidiNoteOn,
    MidiPedal,
    parse_message,
)

MIDDLE_C: Final[int] = 60
VELOCITY: Final[int] = 100


class TestKeys:
    """A note-on presses a key on any channel, and a note-off or a note-on at velocity 0 lifts it."""

    @pytest.mark.parametrize("channel", [0, 9, 15])
    def test_a_note_on_presses_a_key_on_every_channel(self, channel: int) -> None:
        assert parse_message(bytes((0x90 | channel, MIDDLE_C, VELOCITY))) == MidiNoteOn(
            note=MIDDLE_C,
            velocity=VELOCITY,
        )

    def test_a_note_off_lifts_the_key_whatever_its_release_velocity(self) -> None:
        assert parse_message(bytes((0x83, MIDDLE_C, 0x4C))) == MidiNoteOff(note=MIDDLE_C)

    def test_a_note_on_at_velocity_zero_lifts_the_key(self) -> None:
        assert parse_message(bytes((0x90, MIDDLE_C, 0))) == MidiNoteOff(note=MIDDLE_C)

    def test_the_lowest_velocity_still_presses(self) -> None:
        assert parse_message(bytes((0x90, MIDDLE_C, 1))) == MidiNoteOn(note=MIDDLE_C, velocity=1)


class TestThePedal:
    """The sustain pedal is down from the middle of its travel up, and resetting the controllers lifts it."""

    @pytest.mark.parametrize(("value", "down"), [(0, False), (63, False), (64, True), (127, True)])
    def test_the_pedal_switches_at_the_middle(self, value: int, down: bool) -> None:
        assert parse_message(bytes((0xB0, 64, value))) == MidiPedal(down=down)

    def test_resetting_the_controllers_lifts_the_pedal(self) -> None:
        assert parse_message(bytes((0xB0, 121, 0))) == MidiPedal(down=False)

    @pytest.mark.parametrize("controller", [120, 123])
    def test_the_silencing_controllers_let_every_key_go(self, controller: int) -> None:
        assert parse_message(bytes((0xB0, controller, 0))) == MidiAllNotesOff()

    @pytest.mark.parametrize("controller", [1, 7, 65, 122])
    def test_other_controllers_play_nothing(self, controller: int) -> None:
        assert parse_message(bytes((0xB0, controller, 127))) is None


class TestWhatPlaysNothing:
    """Messages the application plays nothing for, and bytes forming no channel message, read as ``None``."""

    @pytest.mark.parametrize(
        "message",
        [
            bytes((0xE0, 0x00, 0x40)),
            bytes((0xA0, MIDDLE_C, 30)),
            bytes((0xC0, 5)),
            bytes((0xD0, 30)),
            bytes((0xF8,)),
            bytes((0xF2, 0x10, 0x00)),
        ],
        ids=["pitch-bend", "key-pressure", "program", "channel-pressure", "clock", "song-position"],
    )
    def test_a_message_the_application_plays_nothing_for(self, message: bytes) -> None:
        assert parse_message(message) is None

    @pytest.mark.parametrize(
        "message",
        [
            b"",
            bytes((0x90, MIDDLE_C)),
            bytes((0x90, MIDDLE_C, VELOCITY, 0)),
            bytes((MIDDLE_C, VELOCITY, 0)),
            bytes((0x90, 0x80, VELOCITY)),
            bytes((0x90, MIDDLE_C, 0x80)),
        ],
        ids=["empty", "short", "long", "no-status", "status-as-note", "status-as-velocity"],
    )
    def test_broken_bytes_read_as_nothing(self, message: bytes) -> None:
        assert parse_message(message) is None
