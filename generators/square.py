from typing import List

import numpy as np

from config import Config
from constants import DUTY_CYCLES, MAX_VOLUME, MIXER_SQUARE
from generators.generator import Generator
from generators.types import Initials
from instructions.square import SquareInstruction
from timers.phase import PhaseTimer


class SquareGenerator(Generator):
    def __init__(self, config: Config, name: str = "square") -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.sample_rate,
            change_rate=config.change_rate,
            reset_phase=config.reset_phase,
            phase_increment=1.0,
        )

    def __call__(
        self,
        square_instruction: SquareInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)

        if not square_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(square_instruction, initials=initials)
        self.save_state(save, square_instruction, initials)

        return output * MIXER_SQUARE * self.config.mixer

    def set_timer(self, square_instruction: SquareInstruction) -> None:
        if square_instruction.on:
            self.timer.frequency = self.get_frequency(square_instruction.pitch)
        else:
            self.timer.frequency = 0.0

    def apply(self, output: np.ndarray, square_instruction: SquareInstruction) -> np.ndarray:
        duty_cycle = DUTY_CYCLES[square_instruction.duty_cycle]
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= square_instruction.volume / MAX_VOLUME
        return output

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

    @classmethod
    def class_name(cls) -> str:
        return cls.__name__
