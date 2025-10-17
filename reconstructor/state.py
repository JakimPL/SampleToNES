from typing import Dict, Generic, List, Self

import numpy as np
from pydantic import BaseModel

from instructions.instruction import Instruction
from library.fragment import Fragment
from reconstructor.approximation import FragmentApproximation
from typehints.general import Initials
from typehints.instructions import InstructionType


class FragmentReconstructionState(BaseModel):
    fragment: Fragment
    instruction: Instruction
    error: float

    class Config:
        arbitrary_types_allowed = True


class ReconstructionState(BaseModel, Generic[InstructionType]):
    generator_names: List[str] = []
    instructions: Dict[str, List[InstructionType]] = {}
    approximations: Dict[str, List[np.ndarray]] = {}
    initials: Dict[str, Initials] = {}
    errors: Dict[str, List[float]] = {}

    @classmethod
    def create(cls, generator_names: List[str]) -> Self:
        return cls(
            generator_names=generator_names,
            instructions={name: [] for name in generator_names},
            approximations={name: [] for name in generator_names},
            initials={name: None for name in generator_names},
            errors={name: [] for name in generator_names},
        )

    def append(self, fragment_approximation: FragmentApproximation) -> None:
        name = fragment_approximation.generator_name
        self.instructions[name].append(fragment_approximation.instruction)
        self.approximations[name].append(fragment_approximation.fragment.audio)
        self.initials[name] = fragment_approximation.terminals
        self.errors[name].append(fragment_approximation.error)

    @property
    def total_error(self) -> float:
        return sum(sum(errors) for errors in self.errors.values())

    class Config:
        arbitrary_types_allowed = True
