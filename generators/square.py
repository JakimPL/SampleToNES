from typing import List, Optional

import numpy as np

from constants import DUTY_CYCLES, MAX_VOLUME, MIXER_SQUARE, VOLUME_RANGE
from generators.generator import Generator
from instructions.square import SquareInstruction


class SquareGenerator(Generator):
    def __call__(
        self,
        square_instruction: SquareInstruction,
        initial_phase: Optional[float] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        self.validate_initials(initial_phase, initial_clock)
        output = np.zeros(self.frame_length, dtype=np.float32)

        if not square_instruction.on or square_instruction.pitch is None:
            return output

        if initial_phase is None or (
            self.previous_instruction is not None
            and (
                (self.previous_instruction.on and self.previous_instruction.pitch != square_instruction.pitch)
                or (not self.previous_instruction.on)
            )
        ):
            self.timer.phase = 0.0

        self.timer.frequency = self.get_frequency(square_instruction.pitch)
        duty_cycle = DUTY_CYCLES[square_instruction.duty_cycle]

        output = self.timer(self.frame_length, initial_phase=initial_phase)
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= square_instruction.volume / MAX_VOLUME

        return output * MIXER_SQUARE

    def get_possible_instructions(self) -> List[SquareInstruction]:
        square_instructions = [SquareInstruction(on=False, pitch=None, volume=0, duty_cycle=0)]

        for pitch in self.frequency_table:
            for volume in VOLUME_RANGE:
                for duty_cycle in range(len(DUTY_CYCLES)):
                    square_instructions.append(
                        SquareInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)
                    )

        return square_instructions

    def validate_initials(self, initial_phase: Optional[int], initial_clock: Optional[float]) -> None:
        if initial_phase is not None:
            if not isinstance(initial_phase, float) or (initial_phase < 0.0 or initial_phase >= 1.0):
                raise ValueError("Initial phase for SquareGenerator must be between 0.0 and 1.0")

        if initial_clock is not None:
            raise ValueError("Initial clock for SquareGenerator must be None")
