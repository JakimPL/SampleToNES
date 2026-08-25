from math import ceil
from typing import Final

from sampletones_core.timing.rate import RowRate
from sampletones_shared.constants.nes import MAX_NES_FREQUENCY
from sampletones_shared.constants.project import MAX_SPEED, MIN_TEMPO

MIN_TICKS_PER_ROW: Final[int] = 1
MAX_TICKS_PER_ROW: Final[int] = ceil(
    RowRate.from_parameters(
        tempo=MIN_TEMPO,
        speed=MAX_SPEED,
        nes_frequency=MAX_NES_FREQUENCY,
    ).ticks_per_row
)
