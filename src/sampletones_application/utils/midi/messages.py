from dataclasses import dataclass
from typing import Final, FrozenSet, Optional, Union

STATUS_FLAG: Final[int] = 0x80
COMMAND_MASK: Final[int] = 0xF0
NOTE_OFF: Final[int] = 0x80
NOTE_ON: Final[int] = 0x90
CONTROL_CHANGE: Final[int] = 0xB0
SUSTAIN_PEDAL: Final[int] = 64
RESET_ALL_CONTROLLERS: Final[int] = 121
ALL_NOTES_OFF_CONTROLLERS: Final[FrozenSet[int]] = frozenset({120, 123})
PEDAL_DOWN_THRESHOLD: Final[int] = 64
CHANNEL_MESSAGE_LENGTH: Final[int] = 3


@dataclass(frozen=True)
class MidiNoteOn:
    """A key pressed: its note number and how hard it was struck.

    Attributes:
        note: The MIDI note number, 0 to 127.
        velocity: How hard the key was struck, 1 to 127.
    """

    note: int
    velocity: int


@dataclass(frozen=True)
class MidiNoteOff:
    """A key lifted.

    Attributes:
        note: The MIDI note number, 0 to 127.
    """

    note: int


@dataclass(frozen=True)
class MidiPedal:
    """The sustain pedal moved to one side of its middle.

    Attributes:
        down: Whether the pedal is down.
    """

    down: bool


@dataclass(frozen=True)
class MidiAllNotesOff:
    """Every key the keyboard sounds is let go at once, as its panic button or a lost port asks."""


MidiMessage = Union[MidiNoteOn, MidiNoteOff, MidiPedal, MidiAllNotesOff]


def parse_message(message: bytes) -> Optional[MidiMessage]:
    """What one complete MIDI 1.0 message means to the application, read from its wire bytes.

    Every MIDI library hands over these bytes, status byte first, so reading them here keeps the meaning the
    same whichever library delivers them. Every channel counts as one keyboard. A note-on at velocity 0 is a
    note-off, as the standard has it. The sustain pedal is down from the middle of its travel up, so a pedal
    sending a smooth ramp switches once each way. Resetting the controllers lifts the pedal, and the two
    controllers that silence a keyboard let every key go.

    Args:
        message: One complete message, status byte first.

    Returns:
        Optional[MidiMessage]: What the message means, or ``None`` for a message the application plays nothing
            for, and for bytes that form no channel message.
    """
    if not _is_channel_message(message):
        return None

    command, first, second = message[0] & COMMAND_MASK, message[1], message[2]
    if command == NOTE_ON and second > 0:
        return MidiNoteOn(note=first, velocity=second)

    if command in (NOTE_ON, NOTE_OFF):
        return MidiNoteOff(note=first)

    if command == CONTROL_CHANGE:
        return _controller(first, second)

    return None


def _is_channel_message(message: bytes) -> bool:
    """Whether ``message`` is a whole three-byte channel message: one status byte, then two data bytes."""
    return (
        len(message) == CHANNEL_MESSAGE_LENGTH
        and message[0] & STATUS_FLAG != 0
        and message[0] & COMMAND_MASK != COMMAND_MASK
        and all(data & STATUS_FLAG == 0 for data in message[1:])
    )


def _controller(controller: int, value: int) -> Optional[MidiMessage]:
    if controller == SUSTAIN_PEDAL:
        return MidiPedal(down=value >= PEDAL_DOWN_THRESHOLD)

    if controller == RESET_ALL_CONTROLLERS:
        return MidiPedal(down=False)

    if controller in ALL_NOTES_OFF_CONTROLLERS:
        return MidiAllNotesOff()

    return None
