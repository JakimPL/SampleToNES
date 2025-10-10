from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from config import Config
from ffts.fft import calculate_log_arfft
from ffts.window import Window
from frequencies import get_frequency_table
from instructions.instruction import Instruction
from reconstructor.criterion import Criterion
from timers.timer import Timer


class Generator:
    def __init__(self, config: Config, name: str) -> None:
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
        save: bool = False,
        window: Optional[Window] = None,
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
        fragment_feature: np.ndarray,
        criterion: Criterion,
        initials: Optional[Tuple[Any, ...]] = None,
    ) -> Tuple[np.ndarray, Instruction, float]:
        instructions = []
        errors = []
        features = []
        for instruction in self.get_possible_instructions():
            approximation = self(instruction, initials=initials, save=False, window=criterion.window)
            approximation_feature = calculate_log_arfft(approximation, criterion.window.size)
            error = criterion(fragment_feature, approximation_feature, instruction, self.previous_instruction)
            features.append(approximation_feature)
            instructions.append(instruction)
            errors.append(error)

        index = np.argmin(errors)
        feature = features[index]
        instruction = instructions[index]
        error = errors[index]
        return feature, instruction, error

    def find_best_fragment_approximation(
        self,
        fragment_feature: np.ndarray,
        criterion: Criterion,
        initials: Optional[Tuple[Any, ...]] = None,
    ) -> Tuple[np.ndarray, Instruction, np.ndarray, float]:
        feature, instruction, error = self.find_best_instruction(fragment_feature, criterion, initials=initials)
        approximation = self(instruction, initials=initials, save=True)
        plt.plot(approximation)
        plt.show()
        return approximation, instruction, feature, error

    @property
    def frame_length(self) -> int:
        return self.config.frame_length

    @staticmethod
    def get_instruction_type() -> type:
        raise NotImplementedError("Subclasses must implement this method")
