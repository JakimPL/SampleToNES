from enum import StrEnum
from typing import Dict, Final

from sampletones_core.constants.general import APU_CLOCK
from sampletones_shared.constants.music import A4_FREQUENCY

CHIP_TYPE_NES: Final[str] = "nes"


class ChipVariant(StrEnum):
    """NES system whose CPU clock drives the tuning table."""

    NTSC = "NTSC"
    PAL = "PAL"
    DENDY = "Dendy"


CPU_FREQUENCIES: Final[Dict[ChipVariant, int]] = {
    ChipVariant.NTSC: int(APU_CLOCK),
    ChipVariant.PAL: 1_662_607,
    ChipVariant.DENDY: 1_773_448,
}

DEFAULT_CHIP_VARIANT: Final[ChipVariant] = ChipVariant.NTSC
DEFAULT_CPU_FREQUENCY: Final[int] = CPU_FREQUENCIES[DEFAULT_CHIP_VARIANT]

TUNING_TABLE_LENGTH: Final[int] = 96
TUNING_A4_INDEX: Final[int] = 45
TUNING_PERIOD_DIVISOR: Final[int] = 16
MIN_TUNING_PERIOD: Final[int] = 1
MAX_TUNING_PERIOD: Final[int] = 2047
PERIOD_OVER_TIMER: Final[int] = 1

DEFAULT_A4_TUNING: Final[float] = A4_FREQUENCY
MIN_A4_TUNING: Final[float] = 220.0
MAX_A4_TUNING: Final[float] = 880.0

MIN_INITIAL_SPEED: Final[int] = 1
MAX_INITIAL_SPEED: Final[int] = 255
SPEED_CLOCK_TEMPO: Final[int] = 0
