from typing import List, Optional

import numpy as np

from constants import MAX_VOLUME, VOLUME_RANGE
from generators.generator import Generator
from instructions.square import SquareInstruction

DUTY_CYCLES = [0.125, 0.25, 0.5, 0.75]
MIXER_SQUARE = 0.8836662749706228


class SquareGenerator(Generator):
    def __call__(self, square_instruction: SquareInstruction, initial_phase: Optional[float] = None) -> np.ndarray:
        output = np.zeros(self.frames, dtype=np.float32)

        if not square_instruction.on or square_instruction.pitch is None:
            return output

        self.timer.frequency = self.get_frequency(square_instruction.pitch)
        duty_cycle = DUTY_CYCLES[square_instruction.duty_cycle]

        output = self.timer(self.frames, initial_phase=initial_phase)
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= square_instruction.volume / MAX_VOLUME

        return output * MIXER_SQUARE

    def get_possible_instructions(self) -> List[SquareInstruction]:
        square_instructions = [
            SquareInstruction(
                on=False,
                pitch=None,
                volume=0,
                duty_cycle=0
            )
        ]

        for pitch in self.frequency_table:
            for volume in VOLUME_RANGE:
                for duty_cycle in range(len(DUTY_CYCLES)):
                    square_instructions.append(SquareInstruction(
                        on=True,
                        pitch=pitch,
                        volume=volume,
                        duty_cycle=duty_cycle
                    ))

        return square_instructions
