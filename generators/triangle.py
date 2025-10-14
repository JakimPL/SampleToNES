from typing import List, Tuple

import numpy as np

from config import Config
from constants import MIXER_TRIANGLE, TRIANGLE_OFFSET
from ffts.window import Window
from generators.generator import Generator
from generators.types import Initials
from instructions.triangle import TriangleInstruction
from timers.phase import PhaseTimer


class TriangleGenerator(Generator):
    def __init__(self, config: Config, name: str = "triangle") -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.sample_rate,
            change_rate=config.change_rate,
            reset_phase=config.reset_phase,
            phase_increment=0.5,
        )

    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)

        if not triangle_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(triangle_instruction, initials=initials)
        self.save_state(save, triangle_instruction, initials)

        return output * MIXER_TRIANGLE * self.config.mixer

    def set_timer(self, triangle_instruction: TriangleInstruction) -> None:
        if triangle_instruction.on:
            self.timer.frequency = self.get_frequency(triangle_instruction.pitch)
        else:
            self.timer.frequency = 0.0

    def apply(self, output: np.ndarray, triangle_instruction: TriangleInstruction) -> np.ndarray:
        return 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5

    def get_possible_instructions(self) -> List[TriangleInstruction]:
        triangle_instructions = [
            TriangleInstruction(
                on=False,
                pitch=None,
            )
        ]

        for pitch in self.frequency_table:
            triangle_instructions.append(
                TriangleInstruction(
                    on=True,
                    pitch=pitch,
                )
            )

        return triangle_instructions

    @staticmethod
    def get_instruction_type() -> type:
        return TriangleInstruction

    @classmethod
    def class_name(cls) -> str:
        return cls.__name__
