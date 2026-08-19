from typing import Dict, List, Self

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion

from .approximation import ApproximationData


class FragmentReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    fragment: Fragment
    instruction: InstructionUnion


class ReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    channel_names: List[ChannelName] = []
    instructions: Dict[ChannelName, List[InstructionUnion]] = {}
    approximations: Dict[ChannelName, List[np.ndarray]] = {}

    @classmethod
    def create(cls, channel_names: List[ChannelName]) -> Self:
        return cls(
            channel_names=channel_names,
            instructions={name: [] for name in channel_names},
            approximations={name: [] for name in channel_names},
        )

    def append(
        self,
        fragment_approximation: ApproximationData,
        approximation: np.ndarray,
    ) -> None:
        name = fragment_approximation.channel_name
        self.instructions[name].append(fragment_approximation.instruction)
        self.approximations[name].append(approximation)
