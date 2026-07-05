from enum import IntEnum
from typing import Dict, Final

from sampletones_core.constants.enums import GeneratorName


class ChannelId(IntEnum):
    """Channel identifiers stored in the HEADER block and order table."""

    SQUARE1 = 0
    SQUARE2 = 1
    TRIANGLE = 2
    NOISE = 3
    DPCM = 4


CHANNEL_COUNT_2A03: Final[int] = 5

GENERATOR_NAME_TO_CHANNEL_ID: Final[Dict[GeneratorName, ChannelId]] = {
    GeneratorName.PULSE1: ChannelId.SQUARE1,
    GeneratorName.PULSE2: ChannelId.SQUARE2,
    GeneratorName.TRIANGLE: ChannelId.TRIANGLE,
    GeneratorName.NOISE: ChannelId.NOISE,
}
