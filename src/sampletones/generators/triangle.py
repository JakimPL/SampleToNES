from typing import List

import numpy as np

from sampletones.configs import Config
from sampletones.constants import GeneratorClassName, GeneratorName
from sampletones.constants.general import MIN_PITCH, MIXER_TRIANGLE, TRIANGLE_OFFSET
from sampletones.instructions import TriangleInstruction
from sampletones.timers import PhaseTimer
from sampletones.typehints import Initials

from .generator import Generator


class TriangleGenerator(Generator[TriangleInstruction, PhaseTimer]):
    def __init__(self, config: Config, name: GeneratorName = GeneratorName.TRIANGLE) -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.library.sample_rate,
            change_rate=config.library.change_rate,
            reset_phase=config.generation.reset_phase,
            phase_increment=0.5,
        )

    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        if not isinstance(triangle_instruction, TriangleInstruction):
            raise TypeError("instruction must be an instance of TriangleInstruction")

        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)

        if not triangle_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(triangle_instruction, initials=initials)
        self.save_state(save, triangle_instruction, initials)

        return output

    def set_timer(self, instruction: TriangleInstruction) -> None:
        if instruction.on:
            self.timer.frequency = self.get_frequency(instruction.pitch)
        else:
            self.timer.frequency = 0.0

    def apply(self, output: np.ndarray, instruction: TriangleInstruction) -> np.ndarray:
        triangle = 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5
        return triangle * MIXER_TRIANGLE

    def get_possible_instructions(self) -> List[TriangleInstruction]:
        triangle_instructions = [
            TriangleInstruction(
                on=False,
                pitch=MIN_PITCH,
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
    def class_name(cls) -> GeneratorClassName:
        return GeneratorClassName.TRIANGLE_GENERATOR
