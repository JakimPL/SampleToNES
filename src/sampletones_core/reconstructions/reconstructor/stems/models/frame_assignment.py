from typing import Dict, NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.rest import StemRest


class StemFrameAssignment(NamedTuple):
    """One frame's outcome: the picks that were made and the channels left resting.

    Together the two cover every channel the setup puts in play, which is what lets a
    reconstruction record one entry per channel for each frame.
    """

    choices: Tuple[StemChoice, ...]
    rests: Tuple[StemRest, ...]

    @property
    def by_channel(self) -> Dict[ChannelName, StemChoice]:
        return {choice.channel_name: choice for choice in self.choices}

    @property
    def resting(self) -> Tuple[ChannelName, ...]:
        return tuple(rest.channel_name for rest in self.rests)
