from enum import IntEnum
from typing import Final

from sampletones_core.formats.bitphase.specification.chip import TUNING_TABLE_LENGTH


class NoteName(IntEnum):
    """Reserved values of a pattern cell's note column.

    Pitched notes occupy ``2``..``13`` (C..B); the values below are the non-pitched
    markers.
    """

    NONE = 0
    OFF = 1
    C = 2
    B = 13


NOTE_RANGE: Final[int] = 12
FIRST_OCTAVE: Final[int] = 1
EMPTY_OCTAVE: Final[int] = 0

MIN_NOTE_INDEX: Final[int] = 0
MAX_NOTE_INDEX: Final[int] = TUNING_TABLE_LENGTH - 1
NOTE_INDEX_PITCH_OFFSET: Final[int] = 24
NOISE_BASE_NOTE_INDEX: Final[int] = 48

SYMBOL_BASE: Final[int] = 36
SYMBOL_DIGITS: Final[str] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

NO_INSTRUMENT_CHANGE: Final[int] = 0
NO_TABLE_CHANGE: Final[int] = 0
TABLE_OFF: Final[int] = -1
TABLE_COLUMN_OFFSET: Final[int] = 1

NO_VOLUME_CHANGE: Final[int] = 0
FULL_VOLUME: Final[int] = 15

MIN_PATTERN_LENGTH: Final[int] = 1
MAX_PATTERN_LENGTH: Final[int] = 256

FIRST_PATTERN_ID: Final[int] = 0
