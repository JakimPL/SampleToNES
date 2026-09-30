from enum import IntEnum
from typing import Final


class EffectId(IntEnum):
    """Identifier an effect column carries: the code point of the letter Bitphase prints, or the digit itself.

    ``SPEED`` states how many engine ticks the row it sits on lasts, taken from the effect's
    own parameter or, where the effect names a table, from one table entry per pattern row.
    ``ORNAMENT_POSITION`` places the channel's table at the step its parameter names, on the
    row's own first tick.
    """

    ORNAMENT_POSITION = 5
    SPEED = ord("S")


SPEED_EFFECT_DELAY: Final[int] = 0
ORNAMENT_POSITION_DELAY: Final[int] = 0
MAX_ORNAMENT_POSITION: Final[int] = 0xFF
NO_EFFECT_PARAMETER: Final[int] = 0
NO_EFFECT_TABLE: Final[int] = -1

MIN_EFFECT_COLUMNS: Final[int] = 1
MAX_EFFECT_COLUMNS: Final[int] = 4
