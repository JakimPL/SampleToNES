import math
from typing import Tuple

from sampletones_core.bitphase.specification.chip import (
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
    TUNING_A4_INDEX,
    TUNING_PERIOD_DIVISOR,
    TUNING_TABLE_LENGTH,
)
from sampletones_core.bitphase.specification.patterns import NOTE_RANGE


def generate_tuning_table(
    chip_frequency: int,
    *,
    a4_tuning: float,
    max_period: int = MAX_TUNING_PERIOD,
) -> Tuple[int, ...]:
    """Builds the channel period Bitphase plays for each of its 96 note indices.

    Each index is one equal-tempered semitone, measured from the concert pitch that
    sits at index 45, and its period is the CPU clock divided by the timer's own
    divisor and the note's frequency. Rounding matches the tracker's, so a table built
    here equals the one Bitphase derives from the same settings.

    Args:
        chip_frequency: CPU clock in Hz.
        a4_tuning: Frequency in Hz of the note at the concert-pitch index.
        max_period: Longest period the channel timer holds.

    Returns:
        Tuple[int, ...]: One period per note index, held within the timer's range.
    """
    periods = []
    for index in range(TUNING_TABLE_LENGTH):
        frequency = a4_tuning * 2 ** ((index - TUNING_A4_INDEX) / NOTE_RANGE)
        period = math.floor(chip_frequency / TUNING_PERIOD_DIVISOR / frequency + 0.5)
        periods.append(max(MIN_TUNING_PERIOD, min(max_period, period)))

    return tuple(periods)
