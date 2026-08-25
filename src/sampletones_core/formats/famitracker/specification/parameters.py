from enum import IntEnum
from typing import Final


class Machine(IntEnum):
    """Playback machine stored in the PARAMS block."""

    NTSC = 0
    PAL = 1


EXPANSION_NONE: Final[int] = 0
DEFAULT_VIBRATO_STYLE: Final[int] = 1
DEFAULT_HIGHLIGHT_FIRST: Final[int] = 4
DEFAULT_HIGHLIGHT_SECOND: Final[int] = 16
ENGINE_SPEED_MACHINE_DEFAULT: Final[int] = 0
SINGLE_TRACK_COUNT: Final[int] = 1
FIRST_TRACK_INDEX: Final[int] = 0

DEFAULT_SPEED_SPLIT_POINT: Final[int] = 32

COMMENT_HIDDEN_ON_OPEN: Final[int] = 0
