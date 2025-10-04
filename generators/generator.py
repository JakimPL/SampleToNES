from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from config import Config
from frequencies import get_frequency_table
from instructions.instruction import Instruction
from reconstructor.criterion import Criterion
from reconstructor.state import ReconstructionState
from timers.timer import Timer


class Generator:
    def __init__(self, name: str, config: Config) -> None:
        self.config: Config = config
        self.frequency_table: Dict[int, float] = get_frequency_table(config)

        self.name: str = name
        self.clock: Optional[float] = None
        self.previous_instruction: Optional[Instruction] = None
        self.timer: Timer

    def __call__(
        self,
        instruction: Instruction,
        initials: Optional[Tuple[Any, ...]] = None,
        length: Optional[int] = None,
        direction: bool = True,
        save: bool = False,
    ) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        self.previous_instruction = None
        self.timer.reset()

    def validate(self, *initials: Any) -> None:
        self.timer.validate(*initials)

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.timer.initials

    def get_frequency(self, pitch: int) -> Optional[float]:
        return self.frequency_table.get(pitch, None)

    def get_possible_instructions(self) -> List[Instruction]:
        raise NotImplementedError("Subclasses must implement this method")

    def find_best_instruction(
        self,
        audio: np.ndarray,
        state: ReconstructionState,
        criterion: Criterion,
        initials: Optional[Tuple[Any, ...]] = None,
    ) -> Tuple[Instruction, float]:
        instructions = []
        errors = []
        for instruction in self.get_possible_instructions():
            approximation = self(instruction, initials=initials)
            error = criterion(audio, approximation, state, instruction, self.previous_instruction)
            instructions.append(instruction)
            errors.append(error)

        index = np.argmin(errors)
        instruction = instructions[index]
        error = errors[index]
        return instruction, error

    def find_best_fragment_approximation(
        self,
        audio: np.ndarray,
        state: ReconstructionState,
        criterion: Criterion,
        initials: Optional[Tuple[Any, ...]] = None,
    ) -> Tuple[np.ndarray, Instruction, float]:
        instruction, error = self.find_best_instruction(audio, state, criterion, initials=initials)
        approximation = self(instruction, initials=initials, save=True)
        return approximation, instruction, error

    @property
    def frame_length(self) -> int:
        return self.config.frame_length

    @staticmethod
    def get_instruction_type() -> type:
        raise NotImplementedError("Subclasses must implement this method")
