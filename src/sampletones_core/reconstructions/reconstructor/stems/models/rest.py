from typing import NamedTuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.matching import Column


class StemRest(NamedTuple):
    """One channel's frame that every stem left free: the null instruction it holds, alone.

    A rest reaches the decoder as a column like any other, one state wide, so the channel keeps
    its place in the frame and the silence it sounds is the frame's own answer.
    """

    channel_name: ChannelName
    column: Column
