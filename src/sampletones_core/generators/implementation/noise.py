from typing import ClassVar, List, Type

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.constants.general import (
    MAX_VOLUME,
    MIXER_NOISE,
    NOISE_PERIODS,
)
from sampletones_core.instructions import InstructionTypeUnion, NoiseInstruction
from sampletones_core.timers import LFSRTimer

from ..generator import Generator


class NoiseGenerator(Generator[NoiseInstruction, LFSRTimer]):
    instruction_type: ClassVar[Type[NoiseInstruction]] = NoiseInstruction

    def __init__(
        self,
        config: Config,
        name: str = ChannelName.NOISE,
    ) -> None:
        super().__init__(config, name)
        self.timer = LFSRTimer(
            sample_rate=config.library.sample_rate,
            nes_frequency=config.library.nes_frequency,
            reset_phase=config.generation.reset_phase,
        )

    def set_timer(self, instruction: NoiseInstruction) -> None:
        if instruction.on:
            self.timer.short = instruction.short
            self.timer.period = instruction.period
        else:
            self.timer.short = False
            self.timer.period = 0

    def apply(self, output: np.ndarray, instruction: NoiseInstruction) -> np.ndarray:
        volume = np.float32(MIXER_NOISE * float(instruction.volume) / float(MAX_VOLUME))
        return volume * output

    def get_possible_instructions(self) -> List[NoiseInstruction]:
        noise_instructions = [
            NoiseInstruction(
                on=False,
                period=0,
                volume=0,
                short=False,
            ),
        ]

        for period in range(len(NOISE_PERIODS)):
            for volume in range(1, MAX_VOLUME + 1):
                for short in [False, True]:
                    noise_instructions.append(
                        NoiseInstruction(
                            on=True,
                            period=period,
                            volume=volume,
                            short=short,
                        )
                    )

        return noise_instructions

    @classmethod
    def get_instruction_type(cls) -> InstructionTypeUnion:
        return NoiseInstruction

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        return GeneratorClassName.NOISE_GENERATOR
