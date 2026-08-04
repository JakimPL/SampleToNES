from typing import Final

from sampletones_core.constants.general import MAX_DUTY_CYCLE, MAX_VOLUME
from sampletones_core.formats.bitphase.specification.patterns import (
    SYMBOL_BASE,
    TABLE_COLUMN_OFFSET,
)

INSTRUMENT_ID_DIGITS: Final[int] = 2
MIN_INSTRUMENT_ID: Final[int] = 1
MAX_INSTRUMENT_ID: Final[int] = SYMBOL_BASE**INSTRUMENT_ID_DIGITS - 1

TABLE_COLUMN_DIGITS: Final[int] = 1
MAX_TABLE_COLUMN: Final[int] = SYMBOL_BASE**TABLE_COLUMN_DIGITS - 1
MIN_TABLE_ID: Final[int] = 0
MAX_TABLE_ID: Final[int] = MAX_TABLE_COLUMN - TABLE_COLUMN_OFFSET

MIN_PULSE_WIDTH: Final[int] = 0
MAX_PULSE_WIDTH: Final[int] = MAX_DUTY_CYCLE
FLAT_PULSE_WIDTH: Final[int] = 0

MIN_VOLUME_OR_RATE: Final[int] = 0
MAX_VOLUME_OR_RATE: Final[int] = MAX_VOLUME
SILENT_VOLUME: Final[int] = 0

NOISE_MODE_LONG: Final[int] = 0
NOISE_MODE_SHORT: Final[int] = 1

MIN_SOUND_LENGTH: Final[int] = 0
MAX_SOUND_LENGTH: Final[int] = 511
SUSTAINED_SOUND_LENGTH: Final[int] = 0

MIN_TONE_ADD: Final[int] = -4096
MAX_TONE_ADD: Final[int] = 4095
NO_TONE_OFFSET: Final[int] = 0

MIN_SWEEP_RATE: Final[int] = 0
MAX_SWEEP_RATE: Final[int] = 7
MIN_SWEEP_SHIFT: Final[int] = -7
MAX_SWEEP_SHIFT: Final[int] = 7
NO_SWEEP_RATE: Final[int] = 0
NO_SWEEP_SHIFT: Final[int] = 0

CONSTANT_VOLUME: Final[bool] = False
ABSOLUTE_TONE: Final[bool] = False
KEEP_PHASE: Final[bool] = False
NO_SWEEP: Final[bool] = False

LOOP_FROM_START: Final[int] = 0
NO_TABLE_OFFSET: Final[int] = 0
