from typing import Any, List, Optional, Tuple

import numpy as np

from config import Config
from constants import MIXER_TRIANGLE, TRIANGLE_OFFSET
from generators.generator import Generator
from instructions.triangle import TriangleInstruction
from timers.phase import PhaseTimer


class TriangleGenerator(Generator):
    def __init__(self, name: str, config: Config) -> None:
        super().__init__(name, config)
        self.timer = PhaseTimer(sample_rate=config.sample_rate, phase_increment=0.5)

    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initials: Optional[Tuple[Any, ...]] = None,
        length: Optional[int] = None,
        direction: bool = True,
        save: bool = False,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)
        frame_length = self.frame_length if length is None else length
        output = np.zeros(frame_length, dtype=np.float32)

        if not triangle_instruction.on or triangle_instruction.pitch is None:
            return output

        if initial_phase is None or (self.previous_instruction is not None and not self.previous_instruction.on):
            self.timer.reset()
            initial_phase = None

        self.timer.frequency = self.get_frequency(triangle_instruction.pitch)
        output = self.timer(frame_length, direction=direction, initial_phase=initial_phase)
        output = 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5

        if not save:
            self.timer.set(initials)
        else:
            self.previous_instruction = triangle_instruction

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
