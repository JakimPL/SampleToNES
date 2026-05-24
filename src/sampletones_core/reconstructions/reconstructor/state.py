from typing import Dict, List, Self

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion

from .approximation import ApproximationData


class FragmentReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fragment: Fragment
    instruction: InstructionUnion


class ReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_names: List[GeneratorName] = []
    instructions: Dict[GeneratorName, List[InstructionUnion]] = {}
    approximations: Dict[GeneratorName, List[np.ndarray]] = {}

    @classmethod
    def create(cls, generator_names: List[GeneratorName]) -> Self:
        return cls(
            generator_names=generator_names,
            instructions={name: [] for name in generator_names},
            approximations={name: [] for name in generator_names},
        )

    def append(self, fragment_approximation: ApproximationData, approximation: np.ndarray) -> None:
        name = fragment_approximation.generator_name
        self.instructions[name].append(fragment_approximation.instruction)
        self.approximations[name].append(approximation)
