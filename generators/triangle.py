from typing import List, Optional

import numpy as np

from constants import MIXER_TRIANGLE, TRIANGLE_OFFSET
from generators.generator import Generator
from instructions.triangle import TriangleInstruction


class TriangleGenerator(Generator):
    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initial_phase: Optional[float] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        self.validate_initials(initial_phase, initial_clock)
        output = np.zeros(self.frame_length, dtype=np.float32)

        if not triangle_instruction.on or triangle_instruction.pitch is None:
            return output

        if initial_phase is None or (self.previous_instruction is not None and not self.previous_instruction.on):
            self.timer.phase = 0.0

        self.timer.frequency = self.get_frequency(triangle_instruction.pitch) / 2.0
        output = self.timer(self.frame_length, initial_phase=initial_phase)
        output = 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5

        return output * MIXER_TRIANGLE

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

    def validate_initials(self, initial_phase: Optional[int], initial_clock: Optional[float]) -> None:
        if initial_phase is not None:
            if not isinstance(initial_phase, float) or (initial_phase < 0.0 or initial_phase >= 1.0):
                raise ValueError("Initial phase for TriangleGenerator must be between 0.0 and 1.0")

        if initial_clock is not None:
            raise ValueError("Initial clock for TriangleGenerator must be None")
