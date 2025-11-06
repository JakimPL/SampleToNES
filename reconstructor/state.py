from typing import Dict, List, Self

import numpy as np
from pydantic import BaseModel

from constants.enums import GeneratorName
from library.fragment import Fragment
from reconstructor.approximation import ApproximationData
from typehints.instructions import InstructionUnion


class FragmentReconstructionState(BaseModel):
    fragment: Fragment
    instruction: InstructionUnion
    error: float

    class Config:
        arbitrary_types_allowed = True


class ReconstructionState(BaseModel):
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

    class Config:
        arbitrary_types_allowed = True
