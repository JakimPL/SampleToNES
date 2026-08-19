from typing import Dict, Final, Tuple

from sampletones_core.constants.enums import GeneratorName
from sampletones_player.specification.registers import (
    NOISE_CONTROL,
    NOISE_PERIOD,
    PULSE1_CONTROL,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
    PULSE2_CONTROL,
    PULSE2_TIMER_HIGH,
    PULSE2_TIMER_LOW,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_TIMER_HIGH,
    TRIANGLE_TIMER_LOW,
)

CHANNEL_REGISTER_ADDRESSES: Final[Dict[GeneratorName, Tuple[int, ...]]] = {
    GeneratorName.PULSE1: (PULSE1_CONTROL, PULSE1_TIMER_LOW, PULSE1_TIMER_HIGH),
    GeneratorName.PULSE2: (PULSE2_CONTROL, PULSE2_TIMER_LOW, PULSE2_TIMER_HIGH),
    GeneratorName.TRIANGLE: (TRIANGLE_LINEAR_COUNTER, TRIANGLE_TIMER_LOW, TRIANGLE_TIMER_HIGH),
    GeneratorName.NOISE: (NOISE_CONTROL, NOISE_PERIOD),
}
