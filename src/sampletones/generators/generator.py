from typing import Any, Dict, Generic, List, Optional, Tuple, Union

import numpy as np

from sampletones.configs import Config
from sampletones.constants import GeneratorClassName
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

    def generate(self, instruction: InstructionType, initials: Initials = None) -> np.ndarray:
        self.set_timer(instruction)
        output = self.timer(initials=initials)
        output = self.apply(output, instruction)
        return output

    def generate_window(self, instruction: InstructionType, window: Window, initials: Initials = None) -> np.ndarray:
        if not instruction.on:
            return np.zeros(window.size, dtype=np.float32)

        self.set_timer(instruction)
        output = self.timer.generate_window(window, initials)
        return self.apply(output, instruction)

    def generate_sample(self, instruction: InstructionType, window: Window) -> Tuple[np.ndarray, int]:
        if not instruction.on:
            return np.zeros(window.size * 3, dtype=np.float32), 0

        self.set_timer(instruction)
        output, offset = self.timer.generate_sample(window)
        return self.apply(output, instruction), offset

    def generate_frames(
        self, instruction: InstructionType, frames: Union[int, float] = 3.0, initials: Initials = None
    ) -> np.ndarray:
        previous_initials = self.timer.get()

        self.timer.set(initials)
        if isinstance(frames, float):
            frames = round(frames * self.config.library.sample_rate / self.config.library.frame_length)

        samples = round(frames * self.config.library.sample_rate)
        output = []
        for _ in range(frames):
            frame = self(instruction, save=True)
            output.append(frame)

        self.timer.set(previous_initials)
        return np.concatenate(output)[:samples]

    def save_state(self, save: bool, instruction: InstructionType, initials: Initials) -> None:
        if not save:
            self.timer.set(initials)
        else:
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
