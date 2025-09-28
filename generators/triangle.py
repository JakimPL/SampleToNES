from typing import List, Optional

import numpy as np

from generators.generator import Generator
from instructions.triangle import TriangleInstruction

MIXER_TRIANGLE = 1.0
TRIANGLE_OFFSET = 0.5


class TriangleGenerator(Generator):
    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initial_phase: Optional[float] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        output = np.zeros(self.frames, dtype=np.float32)

        if not triangle_instruction.on or triangle_instruction.pitch is None:
            return output

        if initial_phase is None or (self.previous_instruction is not None and not self.previous_instruction.on):
            self.timer.phase = 0.0

        self.timer.frequency = self.get_frequency(triangle_instruction.pitch)
        output = self.timer(self.frames, initial_phase=initial_phase)
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
