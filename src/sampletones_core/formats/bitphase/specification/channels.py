from enum import IntEnum
from typing import Dict, Final, Tuple

from sampletones_core.constants.enums import GeneratorName


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

GENERATOR_NAME_TO_CHANNEL_INDEX: Final[Dict[GeneratorName, ChannelIndex]] = {
    GeneratorName.PULSE1: ChannelIndex.SQUARE1,
    GeneratorName.PULSE2: ChannelIndex.SQUARE2,
    GeneratorName.TRIANGLE: ChannelIndex.TRIANGLE,
    GeneratorName.NOISE: ChannelIndex.NOISE,
}
