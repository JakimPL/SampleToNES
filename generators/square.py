from typing import Any, List, Optional, Tuple

import numpy as np

from constants import DUTY_CYCLES, MAX_VOLUME, MIXER_SQUARE
from generators.generator import Generator
from instructions.square import SquareInstruction
from timers.phase import PhaseTimer


class SquareGenerator(Generator):
    def __init__(self, name: str, config) -> None:
        super().__init__(name, config)
        self.timer = PhaseTimer(sample_rate=config.sample_rate, phase_increment=1.0)

    def __call__(
        self,
        square_instruction: SquareInstruction,
        initials: Optional[Tuple[Any, ...]] = None,
        length: Optional[int] = None,
        direction: bool = True,
        save: bool = False,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)
        frame_length = self.frame_length if length is None else length
        output = np.zeros(frame_length, dtype=np.float32)

        if not square_instruction.on or square_instruction.pitch is None:
            return output

        if self.previous_instruction is not None and (
            (self.previous_instruction.on and self.previous_instruction.pitch != square_instruction.pitch)
            or (not self.previous_instruction.on)
        ):
            self.timer.reset()
            initial_phase = None

        self.timer.frequency = self.get_frequency(square_instruction.pitch)
        duty_cycle = DUTY_CYCLES[square_instruction.duty_cycle]

        output = self.timer(frame_length, direction=direction, initial_phase=initial_phase)
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= square_instruction.volume / MAX_VOLUME

        if not save:
            self.timer.set(initials)
        else:
            self.previous_instruction = square_instruction

        return output * MIXER_SQUARE

    def get_possible_instructions(self) -> List[SquareInstruction]:
        square_instructions = [SquareInstruction(on=False, pitch=None, volume=0, duty_cycle=0)]

        for pitch in self.frequency_table:
            for volume in range(1, MAX_VOLUME + 1):
                for duty_cycle in range(len(DUTY_CYCLES)):
                    square_instructions.append(
                        SquareInstruction(on=True, pitch=pitch, volume=volume, duty_cycle=duty_cycle)
                    )

        return square_instructions

    @staticmethod
    def get_instruction_type() -> type:
        return SquareInstruction
