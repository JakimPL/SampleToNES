from typing import Dict, NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool
from sampletones_core.reconstructions.reconstructor.stems.models.rest import StemRest


class StemFrameAssignment(NamedTuple):
    """One frame's outcome: the picks that were made, the channels left resting and each stem's pool.

    The picks and rests together cover every channel the setup puts in play, which is what lets a
    reconstruction record one entry per channel for each frame. A joint assignment also pools whole
    combinations of every stem's channels, one pool per stem; an assignment of one channel at a time
    pools none.
    """

    choices: Tuple[StemChoice, ...]
    rests: Tuple[StemRest, ...]
    pools: Tuple[StemPool, ...]

    @property
    def by_channel(self) -> Dict[ChannelName, StemChoice]:
        return {choice.channel_name: choice for choice in self.choices}

    @property
    def resting(self) -> Tuple[ChannelName, ...]:
        return tuple(rest.channel_name for rest in self.rests)
