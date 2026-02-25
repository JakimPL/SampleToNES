from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Tuple

import numpy as np

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.constants.general import MIN_SAMPLE_LENGTH
from sampletones.fft import CyclicArray
from sampletones.instructions import InstructionT, InstructionTypeUnion
from sampletones.timers import TimerT, get_frequency_table
from sampletones.types.data import Initials


class Generator(ABC, Generic[InstructionT, TimerT]):
    def __init__(self, config: Config, name: str) -> None:
        if not isinstance(config, Config):
            raise TypeError("config must be an instance of Config")

        if not isinstance(name, str):
            raise TypeError(f"name must be an instance of str, got {type(name)}")

        self.config: Config = config
        self.frequency_table: Dict[int, float] = get_frequency_table(config)

        self.name: str = name
        self.clock: Optional[float] = None
        self.previous_instruction: Optional[InstructionT] = None

        self.timer: TimerT

    @abstractmethod
    def __call__(
        self,
        instruction: InstructionT,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray: ...

    def generate(
        self,
        instruction: InstructionT,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray:
        self.set_timer(instruction)
        output = self.timer(initials=initials, save=save)
        output = self.apply(output, instruction)
        return output

    def generate_sample(self, instruction: InstructionT) -> CyclicArray:
        if not instruction.on:
            min_sample_length = round(MIN_SAMPLE_LENGTH * self.config.library.sample_rate)
            return CyclicArray(
                array=np.zeros(min_sample_length, dtype=np.float32),
                sample_rate=self.config.library.sample_rate,
            )

        self.set_timer(instruction)
        output = self.timer.generate_sample()
        output.array = self.apply(output.array, instruction)
        return output

    def save_state(self, save: bool, instruction: InstructionT) -> None:
        if save:
            self.previous_instruction = instruction

    @abstractmethod
    def set_timer(self, instruction: InstructionT) -> None: ...

    @abstractmethod
    def apply(self, output: np.ndarray, instruction: InstructionT) -> np.ndarray: ...

    def reset(self) -> None:
        self.previous_instruction = None
        self.timer.reset()

    def validate(self, initials: Initials) -> None:
        self.timer.validate(initials)

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.timer.initials

    def get_frequency(self, pitch: int) -> float:
        return self.frequency_table[pitch]

    @abstractmethod
    def get_possible_instructions(self) -> List[InstructionT]: ...

    @property
    def frame_length(self) -> int:
        return self.config.library.frame_length

    @classmethod
    @abstractmethod
    def class_name(cls) -> GeneratorClassName: ...

    @classmethod
    @abstractmethod
    def get_instruction_type(cls) -> InstructionTypeUnion: ...
