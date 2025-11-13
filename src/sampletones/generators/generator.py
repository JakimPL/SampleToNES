from typing import Any, Dict, Generic, List, Optional, Tuple

import numpy as np

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName
from sampletones.ffts import Window
from sampletones.instructions import InstructionType
from sampletones.timers import TimerType, get_frequency_table
from sampletones.typehints import Initials


class Generator(Generic[InstructionType, TimerType]):
    def __init__(self, config: Config, name: str) -> None:
        if not isinstance(config, Config):
            raise TypeError("config must be an instance of Config")

        if not isinstance(name, str):
            raise TypeError(f"name must be an instance of str, got {type(name)}")

        self.config: Config = config
        self.frequency_table: Dict[int, float] = get_frequency_table(config)

        self.name: str = name
        self.clock: Optional[float] = None
        self.previous_instruction: Optional[InstructionType] = None

        self.timer: TimerType

    def __call__(
        self,
        instruction: InstructionType,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def generate(
        self,
        instruction: InstructionType,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray:
        self.set_timer(instruction)
        output = self.timer(initials=initials, save=save)
        output = self.apply(output, instruction)
        return output

    def generate_sample(self, instruction: InstructionType, window: Window) -> np.ndarray:
        if not instruction.on:
            return np.zeros(window.size, dtype=np.float32)

        self.set_timer(instruction)
        output = self.timer.generate_sample(window)
        return self.apply(output, instruction)

    def save_state(self, save: bool, instruction: InstructionType, initials: Initials) -> None:
        if save:
            self.previous_instruction = instruction

    def set_timer(self, instruction: InstructionType) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def apply(self, output: np.ndarray, instruction: InstructionType) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        self.previous_instruction = None
        self.timer.reset()

    def validate(self, *initials: Any) -> None:
        self.timer.validate(*initials)

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.timer.initials

    def get_frequency(self, pitch: int) -> float:
        return self.frequency_table[pitch]

    def get_possible_instructions(self) -> List[InstructionType]:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def frame_length(self) -> int:
        return self.config.library.frame_length

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def get_instruction_type() -> type:
        raise NotImplementedError("Subclasses must implement this method")
