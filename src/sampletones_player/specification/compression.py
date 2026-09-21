from enum import IntEnum
from math import ceil
from typing import Final

from sampletones_player.specification.binary import (
    BYTE_VALUES,
    MAX_BYTE_VALUE,
    WORD_SIZE,
)
from sampletones_shared.constants.general import BITS_PER_BYTE


class TokenTag(IntEnum):
    """What a token's opcode byte says its top two bits.

    Attributes:
        HOLD: The plane keeps the value it reached, for the ticks the operand counts.
        LITERAL: The plane takes the bytes that follow, one per tick.
        PHRASE: The plane plays a phrase from the table at the pitch it was stored at.
        TRANSPOSED_PHRASE: The plane plays a phrase shifted by the signed byte that follows.

    A phrase opcode spends the top bit of its operand on whether the token states a count of its
    own or plays the count the phrase itself carries, so the ids it names outright are the lower
    half of what a hold or a literal counts.
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
MAX_PHRASE_TICKS: Final[int] = BYTE_VALUES

DEFAULT_COUNT_FLAG: Final[int] = (TOKEN_OPERAND_MASK + 1) >> 1
PHRASE_ID_MASK: Final[int] = DEFAULT_COUNT_FLAG - 1
PHRASE_ID_ESCAPE: Final[int] = PHRASE_ID_MASK
CHEAP_PHRASE_IDS: Final[int] = PHRASE_ID_ESCAPE
MAX_PHRASE_IDS: Final[int] = MAX_BYTE_VALUE
MAX_PHRASE_LENGTH: Final[int] = MAX_BYTE_VALUE

PHRASE_TABLE_COUNT_SIZE: Final[int] = ceil(MAX_PHRASE_IDS.bit_length() / BITS_PER_BYTE)
PHRASE_TABLE_ENTRY_SIZE: Final[int] = WORD_SIZE
PHRASE_LENGTH_SIZE: Final[int] = 1
PHRASE_DEFAULT_SIZE: Final[int] = 1
NO_DEFAULT_COUNT: Final[int] = 0

INITIAL_PLANE_VALUE: Final[int] = 0
BEND_FLAG: Final[int] = 0x80
PITCH_INDEX_MASK: Final[int] = BEND_FLAG - 1

PLANE_STATE_SIZE: Final[int] = 10
