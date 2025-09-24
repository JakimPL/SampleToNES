from typing import List, Optional

import numpy as np

from generators.generator import Generator
from instructions.triangle import TriangleInstruction

MIXER_TRIANGLE = 1.0


class TriangleGenerator(Generator):
    def __call__(self, triangle_instruction: TriangleInstruction, initial_phase: Optional[float] = None) -> np.ndarray:
        output = np.zeros(self.frames, dtype=np.float32)
        if not triangle_instruction.on or triangle_instruction.pitch is None:
            return output

        self.timer.frequency = self.get_frequency(triangle_instruction.pitch)
        output = self.timer(self.frames, initial_phase=initial_phase)
        output = 1.0 - np.round(np.abs(((output + 0.25) % 1.0) - 0.5) * 30.0) / 15.0

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
