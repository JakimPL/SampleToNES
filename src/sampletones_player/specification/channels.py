from typing import Dict, Final, FrozenSet, Tuple

from sampletones_core.constants.enums import ChannelName
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

CHANNEL_REGISTER_ADDRESSES: Final[Dict[ChannelName, Tuple[int, ...]]] = {
    ChannelName.PULSE1: (PULSE1_CONTROL, PULSE1_TIMER_LOW, PULSE1_TIMER_HIGH),
    ChannelName.PULSE2: (PULSE2_CONTROL, PULSE2_TIMER_LOW, PULSE2_TIMER_HIGH),
    ChannelName.TRIANGLE: (TRIANGLE_LINEAR_COUNTER, TRIANGLE_TIMER_LOW, TRIANGLE_TIMER_HIGH),
    ChannelName.NOISE: (NOISE_CONTROL, NOISE_PERIOD),
}

TONE_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(
    {
        ChannelName.PULSE1,
        ChannelName.PULSE2,
        ChannelName.TRIANGLE,
    }
)
