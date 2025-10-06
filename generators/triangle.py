from typing import Any, List, Optional, Tuple

import numpy as np

from config import Config
from constants import MIXER_TRIANGLE, TRIANGLE_OFFSET
from ffts.window import Window
from generators.generator import Generator
from instructions.triangle import TriangleInstruction
from timers.phase import PhaseTimer


class TriangleGenerator(Generator):
    def __init__(self, config: Config, name: str = "triangle") -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.sample_rate,
            change_rate=config.change_rate,
            reset_phase=config.reset_phase,
            phase_increment=0.5,
        )

    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initials: Optional[Tuple[Any, ...]] = None,
        save: bool = False,
        window: Optional[Window] = None,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)
        output = np.zeros(self.frame_length if window is None else window.size, dtype=np.float32)

        if not triangle_instruction.on:
            return output

        self.timer.frequency = self.get_frequency(triangle_instruction.pitch)
        output = self.timer(initials=initials, window=window)
        output = 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5

        if window is not None:
            output *= window.envelope

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

    @staticmethod
    def get_instruction_type() -> type:
        return TriangleInstruction
