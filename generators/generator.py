from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from config import Config
from ffts.window import Window
from frequencies import get_frequency_table
from generators.types import Initials
from instructions.instruction import Instruction
from library.fragment import Fragment
from reconstructor.approximation import FragmentApproximation
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
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def generate(self, instruction: Instruction, initials: Initials = None) -> np.ndarray:
        self.set_timer(instruction)
        output = self.timer(initials=initials)
        output = self.apply(output, instruction)
        return output

    def generate_sample(self, instruction: Instruction, window: Window) -> Tuple[np.ndarray, int]:
        if not instruction.on:
            return np.zeros(self.window.size * 3, dtype=np.float32), 0

        self.set_timer(instruction)
        output, offset = self.timer.generate_sample(window)
        return self.apply(output, instruction), offset

    def generate_frames(
        self, instruction: Instruction, frames: Union[int, float] = 3.0, initials: Initials = None
    ) -> np.ndarray:
        previous_initials = self.timer.get()

        self.timer.set(initials)
        if isinstance(frames, float):
            frames = round(frames * self.config.sample_rate / self.config.frame_length)

        samples = round(frames * self.config.sample_rate)
        output = []
        for _ in range(frames):
            frame = self(instruction, save=True)
            output.append(frame)

        self.timer.set(previous_initials)
        return np.concatenate(output)[:samples]

    def save_state(self, save: bool, instruction: Instruction, initials: Initials) -> None:
        if not save:
            self.timer.set(initials)
        else:
            self.previous_instruction = instruction

    def set_timer(self, instruction: Instruction) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def apply(self, output: np.ndarray, instruction: Instruction) -> np.ndarray:
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
        fragment: Fragment,
        criterion: Criterion,
        initials: Initials = None,
    ) -> Tuple[Instruction, float]:
        instructions = []
        errors = []
        for instruction in self.get_possible_instructions():
            approximation = self(instruction, initials=initials, save=False, window=criterion.window)
            approximation = Fragment.create(approximation, criterion.window)
            error = criterion(fragment, approximation, instruction, self.previous_instruction)
            instructions.append(instruction)
            errors.append(error)

        index = np.argmin(errors)
        instruction = instructions[index]
        error = errors[index]
        return instruction, error

    def find_best_fragment_approximation(
        self,
        fragment: Fragment,
        criterion: Criterion,
        initials: Initials = None,
    ) -> FragmentApproximation:
        instruction, error = self.find_best_instruction(fragment, criterion, initials=initials)
        approximation = self(instruction, initials=initials, save=True, window=criterion.window)
        fragment = Fragment.create(approximation, criterion.window)
        return FragmentApproximation(
            generator_name=self.name,
            fragment=fragment,
            instruction=instruction,
            initials=initials,
            terminals=self.initials,
            error=error,
        )

    @property
    def frame_length(self) -> int:
        return self.config.frame_length

    @classmethod
    def class_name(cls) -> str:
        return NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def get_instruction_type() -> type:
        raise NotImplementedError("Subclasses must implement this method")
