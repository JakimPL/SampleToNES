from enum import IntEnum
from typing import Final


class EffectId(IntEnum):
    """Identifier an effect column carries, as the code point of the letter Bitphase prints.

    ``SPEED`` states how many engine ticks the row it sits on lasts, taken from the effect's
    own parameter or, where the effect names a table, from one table entry per pattern row.
    """

    SPEED = ord("S")


SPEED_EFFECT_DELAY: Final[int] = 0
NO_EFFECT_PARAMETER: Final[int] = 0
