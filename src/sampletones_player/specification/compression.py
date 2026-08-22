from enum import IntEnum
from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_player.specification.binary import WORD_SIZE


class TokenTag(IntEnum):
    """What a token's opcode byte says its top two bits.

    Attributes:
        HOLD: The plane keeps the value it reached, for the ticks the operand counts.
        LITERAL: The plane takes the bytes that follow, one per tick.
        PHRASE: The plane plays a phrase from the table at the pitch it was stored at.
        TRANSPOSED_PHRASE: The plane plays a phrase shifted by the signed byte that follows.
    """

    HOLD = 0x00
    LITERAL = 0x40
    PHRASE = 0x80
    TRANSPOSED_PHRASE = 0xC0


TOKEN_TAG_MASK: Final[int] = 0xC0
TOKEN_OPERAND_MASK: Final[int] = 0x3F

OPCODE_SIZE: Final[int] = 1
PHRASE_COUNT_SIZE: Final[int] = 1
PHRASE_ESCAPE_SIZE: Final[int] = 1
TRANSPOSE_SIZE: Final[int] = 1

MAX_HOLD_TICKS: Final[int] = TOKEN_OPERAND_MASK + 1
MAX_LITERAL_BYTES: Final[int] = TOKEN_OPERAND_MASK + 1
MAX_PHRASE_TICKS: Final[int] = 256

PHRASE_ID_ESCAPE: Final[int] = TOKEN_OPERAND_MASK
CHEAP_PHRASE_IDS: Final[int] = PHRASE_ID_ESCAPE
MAX_PHRASE_IDS: Final[int] = 256
MAX_PHRASE_LENGTH: Final[int] = 255

PHRASE_TABLE_COUNT_SIZE: Final[int] = 1
PHRASE_TABLE_ENTRY_SIZE: Final[int] = WORD_SIZE
PHRASE_LENGTH_SIZE: Final[int] = 1

BYTE_VALUES: Final[int] = 256
MAX_BYTE_VALUE: Final[int] = BYTE_VALUES - 1

INITIAL_PLANE_VALUE: Final[int] = 0

PLANES_PER_CHANNEL: Final[int] = 2
PLANE_COUNT: Final[int] = len(ChannelName.items()) * PLANES_PER_CHANNEL
PLANE_STATE_SIZE: Final[int] = 8
