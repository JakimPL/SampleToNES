from typing import Dict, List, Self

import numpy as np
from pydantic import BaseModel, ConfigDict

from sampletones.constants.enums import GeneratorName
from sampletones.instructions import InstructionUnion
from sampletones.library import Fragment

from .approximation import ApproximationData


class FragmentReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fragment: Fragment
    instruction: InstructionUnion
    error: float


class ReconstructionState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_names: List[GeneratorName] = []
    instructions: Dict[GeneratorName, List[InstructionUnion]] = {}
    approximations: Dict[GeneratorName, List[np.ndarray]] = {}
    errors: Dict[GeneratorName, List[float]] = {}

    @classmethod
    def create(cls, generator_names: List[GeneratorName]) -> Self:
        return cls(
            generator_names=generator_names,
            instructions={name: [] for name in generator_names},
            approximations={name: [] for name in generator_names},
            errors={name: [] for name in generator_names},
        )

    def append(self, fragment_approximation: ApproximationData, approximation: np.ndarray) -> None:
        name = fragment_approximation.generator_name
        self.instructions[name].append(fragment_approximation.instruction)
        self.approximations[name].append(approximation)
        self.errors[name].append(fragment_approximation.error)

    @property
    def total_error(self) -> float:
        return sum(sum(errors) for errors in self.errors.values())
