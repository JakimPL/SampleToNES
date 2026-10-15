from typing import Final, FrozenSet, Optional, Sequence

STATUS_FLAG: Final[int] = 0x80
COMMAND_MASK: Final[int] = 0xF0
SYSTEM_EXCLUSIVE_BYTES: Final[FrozenSet[int]] = frozenset({0xF0, 0xF7})
SHORT_COMMANDS: Final[FrozenSet[int]] = frozenset({0xC0, 0xD0})
SHORT_SYSTEM_MESSAGES: Final[FrozenSet[int]] = frozenset({0xF1, 0xF3})
SONG_POSITION: Final[int] = 0xF2
SYSTEM_COMMAND: Final[int] = 0xF0
FULL_LENGTH: Final[int] = 3
SHORT_LENGTH: Final[int] = 2
SINGLE_LENGTH: Final[int] = 1


def wire_message(packed: Sequence[int]) -> Optional[bytes]:
    """The wire bytes of one PortMidi event, which packs a message into four bytes, status first.

    PortMidi delivers a system exclusive message four bytes at a time, the first event opening with its status
    byte and the rest carrying data bytes alone, so both stay behind with its closing byte.

    Args:
        packed: The event's four bytes.

    Returns:
        Optional[bytes]: The message, or ``None`` for a piece of a system exclusive message.
    """
    status = packed[0]
    if status & STATUS_FLAG == 0 or status in SYSTEM_EXCLUSIVE_BYTES:
        return None

    return bytes(packed[: _message_length(status)])


def _message_length(status: int) -> int:
    """How many bytes a message opening with ``status`` spans, its status byte included."""
    command = status & COMMAND_MASK
    if command != SYSTEM_COMMAND:
        return SHORT_LENGTH if command in SHORT_COMMANDS else FULL_LENGTH

    if status in SHORT_SYSTEM_MESSAGES:
        return SHORT_LENGTH

    return FULL_LENGTH if status == SONG_POSITION else SINGLE_LENGTH
