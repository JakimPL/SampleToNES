from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from config import Config
from frequencies import get_frequency_table
from generators.criterion import Loss
from instructions.instruction import Instruction
from reconstructor.state import ReconstructionState
from timer import Timer


class Generator:
    def __init__(self, name: str, config: Config) -> None:
        self.config: Config = config
        self.criterion: Loss = Loss(name, config)
        self.timer: Timer = Timer(sample_rate=config.sample_rate)
        self.frequency_table: Dict[int, float] = get_frequency_table(
            a4_frequency=config.a4_frequency,
            a4_pitch=config.a4_pitch,
            min_pitch=config.min_pitch,
            max_pitch=config.max_pitch,
        )

        self.name: str = name
        self.clock: Optional[float] = None
        self.previous_instruction: Optional[Instruction] = None

    def __call__(
        self,
        instruction: Instruction,
        initial_phase: Optional[Union[float, int]] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        self.previous_instruction = None
        self.timer.phase = 0.0

    @property
    def phase(self) -> float:
        return self.timer.phase

    def get_frequency(self, pitch: int) -> Optional[float]:
        return self.frequency_table.get(pitch, None)

    def get_possible_instructions(self) -> List[Instruction]:
        raise NotImplementedError("Subclasses must implement this method")

    def find_best_instruction(
        self,
        audio: np.ndarray,
        state: ReconstructionState,
        initial_phase: Optional[float] = None,
        initial_clock: Optional[float] = None,
    ) -> Tuple[Instruction, float]:
        instructions = []
        errors = []
        for instruction in self.get_possible_instructions():
            approximation = self(instruction, initial_phase=initial_phase, initial_clock=initial_clock)
            error = self.criterion(audio, approximation, state, self.name)
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
        initial_phase: Optional[float] = None,
        initial_clock: Optional[float] = None,
    ) -> Tuple[np.ndarray, Instruction, float]:
        instruction, error = self.find_best_instruction(
            audio, state, initial_phase=initial_phase, initial_clock=initial_clock
        )
        approximation = self(instruction, initial_phase=initial_phase, initial_clock=initial_clock)
        self.previous_instruction = instruction
        return approximation, instruction, error

    @property
    def frame_length(self) -> int:
        return self.config.frame_length
