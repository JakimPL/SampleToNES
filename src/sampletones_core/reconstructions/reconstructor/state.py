from typing import Dict, List, Self

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion


class FragmentReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    fragment: Fragment
    instruction: InstructionUnion


class ReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    channel_names: List[ChannelName] = []
    instructions: Dict[ChannelName, List[InstructionUnion]] = {}

    @classmethod
    def create(cls, channel_names: List[ChannelName]) -> Self:
        return cls(
            channel_names=channel_names,
            instructions={name: [] for name in channel_names},
        )

    def append(
        self,
        channel_name: ChannelName,
        instruction: InstructionUnion,
    ) -> None:
        """Records one frame of one channel: what it plays."""
        self.instructions[channel_name].append(instruction)

    def drop(self, channel_name: ChannelName) -> None:
        """Releases a channel's stream, leaving it out of the reconstruction being assembled."""
        self.channel_names.remove(channel_name)
        del self.instructions[channel_name]
