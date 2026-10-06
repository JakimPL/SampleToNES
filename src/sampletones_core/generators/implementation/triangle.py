from typing import List

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import (
    MIN_PITCH,
    MIN_SOUNDING_TRIANGLE_TIMER,
    MIXER_TRIANGLE,
    TRIANGLE_OFFSET,
    TRIANGLE_PHASE_INCREMENT,
)
from sampletones_core.instructions import (
    InstructionTypeUnion,
    TriangleInstruction,
)
from sampletones_core.timers import PhaseTimer
from sampletones_shared.types.data import Initials

from ..tonal import TonalGenerator


class TriangleGenerator(TonalGenerator[TriangleInstruction]):
    """The triangle channel, a fixed-volume wave an octave below a pulse at the same divider.

    A timer below ``MIN_SOUNDING_TRIANGLE_TIMER`` renders the middle of the wave while the timer runs
    on. The sequencer steps above hearing there, and the console's output settles at its mean level.
    """

    def __init__(
        self,
        config: Config,
        name: str = ChannelName.TRIANGLE,
    ) -> None:
        super().__init__(config, name)
        self.timer = PhaseTimer(
            sample_rate=config.library.sample_rate,
            nes_frequency=config.library.nes_frequency,
            reset_phase=config.generation.reset_phase,
            phase_increment=TRIANGLE_PHASE_INCREMENT,
        )

    def __call__(
        self,
        triangle_instruction: TriangleInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        if not isinstance(triangle_instruction, TriangleInstruction):
            raise TypeError("instruction must be an instance of TriangleInstruction")

        self.validate(initials)
        if not triangle_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(
            triangle_instruction,
            initials=initials,
            save=save,
        )

        self.save_state(save, triangle_instruction)

        if self.timer.timer < MIN_SOUNDING_TRIANGLE_TIMER:
            return np.zeros(self.frame_length, dtype=np.float32)

        return output

    def apply(self, output: np.ndarray, instruction: TriangleInstruction) -> np.ndarray:
        triangle = 1.0 - np.round(np.abs(((output + TRIANGLE_OFFSET) % 1.0) - 0.5) * 30.0) / 7.5
        return (triangle * MIXER_TRIANGLE).astype(np.float32)

    def get_possible_instructions(self) -> List[TriangleInstruction]:
        triangle_instructions = [
            TriangleInstruction(
                on=False,
                pitch=MIN_PITCH,
            ),
        ]

        for pitch in self.frequency_table:
            triangle_instructions.append(
                TriangleInstruction(
                    on=True,
                    pitch=pitch,
                )
            )

        return triangle_instructions

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return TriangleInstruction

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        return GeneratorClassName.TRIANGLE_GENERATOR
