from typing import Any, List, Optional, Tuple

import numpy as np

from config import Config
from constants import DUTY_CYCLES, MAX_VOLUME, MIXER_SQUARE
from ffts.window import Window
from generators.generator import Generator
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
        initials: Optional[Tuple[Any, ...]] = None,
        save: bool = False,
        window: Optional[Window] = None,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)
        output = np.zeros(self.frame_length if window is None else window.size, dtype=np.float32)

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

        output = self.timer(initials=initials, window=window)
        output = np.where(output < duty_cycle, 1.0, -1.0)
        output *= square_instruction.volume / MAX_VOLUME

        if window is not None:
            output *= window.envelope

        if not save:
            self.timer.set(initials)
        else:
            self.previous_instruction = square_instruction

        return output * MIXER_SQUARE * self.config.mixer

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
