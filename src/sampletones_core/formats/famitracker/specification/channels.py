from enum import IntEnum
from typing import Dict, Final

from sampletones_core.constants.enums import ChannelName


class ChannelId(IntEnum):
    """Channel identifiers stored in the HEADER block and order table."""

    SQUARE1 = 0
    SQUARE2 = 1
    TRIANGLE = 2
    NOISE = 3
    DPCM = 4


CHANNEL_COUNT_2A03: Final[int] = 5

CHANNEL_TO_ID: Final[Dict[ChannelName, ChannelId]] = {
    ChannelName.PULSE1: ChannelId.SQUARE1,
    ChannelName.PULSE2: ChannelId.SQUARE2,
    ChannelName.TRIANGLE: ChannelId.TRIANGLE,
    ChannelName.NOISE: ChannelId.NOISE,
}
