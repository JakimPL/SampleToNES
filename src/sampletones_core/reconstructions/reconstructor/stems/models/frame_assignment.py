from typing import Dict, NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice


class StemFrameAssignment(NamedTuple):
    """One frame's outcome: the picks that were made and the channels left resting.

    Together the two cover every channel the setup puts in play, which is what lets a
    reconstruction record one entry per channel for each frame.
    """

    choices: Tuple[StemChoice, ...]
    resting: Tuple[ChannelName, ...]

    @property
    def by_channel(self) -> Dict[ChannelName, StemChoice]:
        return {choice.channel_name: choice for choice in self.choices}
