from enum import IntEnum
from typing import Dict, Final, Tuple

from sampletones_core.constants.enums import ChannelName


class ChannelIndex(IntEnum):
    """Position each 2A03 channel takes in a pattern's channel list."""

    SQUARE1 = 0
    SQUARE2 = 1
    TRIANGLE = 2
    NOISE = 3
    DPCM = 4


CHANNEL_LABELS: Final[Tuple[str, ...]] = (
    "Square 1",
    "Square 2",
    "Triangle",
    "Noise",
    "DPCM",
)
CHANNEL_COUNT: Final[int] = len(CHANNEL_LABELS)

CHANNEL_TO_INDEX: Final[Dict[ChannelName, ChannelIndex]] = {
    ChannelName.PULSE1: ChannelIndex.SQUARE1,
    ChannelName.PULSE2: ChannelIndex.SQUARE2,
    ChannelName.TRIANGLE: ChannelIndex.TRIANGLE,
    ChannelName.NOISE: ChannelIndex.NOISE,
}
