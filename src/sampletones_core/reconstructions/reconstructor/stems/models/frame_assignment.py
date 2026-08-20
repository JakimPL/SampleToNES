from typing import Dict, NamedTuple, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice


class StemFrameAssignment(NamedTuple):
    choices: Tuple[StemChoice, ...]

    @property
    def by_channel(self) -> Dict[ChannelName, StemChoice]:
        return {choice.channel_name: choice for choice in self.choices}
