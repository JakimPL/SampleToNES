from enum import IntEnum
from typing import Final

NOTE_RANGE: Final[int] = 12
OCTAVE_RANGE: Final[int] = 8


class NoteValue(IntEnum):
    """Reserved values of a pattern cell's note column.

    Pitched notes occupy ``1``..``12`` (C..B); the values below are the non-pitched
    markers.
    """

    NONE = 0
    C = 1
    B = 12
    RELEASE = 13
    HALT = 14


EMPTY_NOTE: Final[int] = 0
EMPTY_INSTRUMENT: Final[int] = 0x40
EMPTY_VOLUME: Final[int] = 0x10
EMPTY_EFFECT: Final[int] = 0
EMPTY_EFFECT_PARAM: Final[int] = 0
DEFAULT_EFFECT_COLUMNS: Final[int] = 1

MIN_OCTAVE: Final[int] = 0
MAX_OCTAVE: Final[int] = 7
PITCH_OCTAVE_OFFSET: Final[int] = 2
FT_MIN_PITCH: Final[int] = (MIN_OCTAVE + PITCH_OCTAVE_OFFSET) * NOTE_RANGE
FT_MAX_PITCH: Final[int] = (MAX_OCTAVE + PITCH_OCTAVE_OFFSET) * NOTE_RANGE + (NOTE_RANGE - 1)

MAX_FRAMES: Final[int] = 128
MAX_PATTERNS: Final[int] = 128
MAX_PATTERN_INDEX: Final[int] = MAX_PATTERNS - 1
DPCM_EMPTY_PATTERN_INDEX: Final[int] = 0
