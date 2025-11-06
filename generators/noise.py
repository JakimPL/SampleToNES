from typing import List

import numpy as np

from configs.config import Config
from constants.enums import GeneratorClassName, GeneratorName
from constants.general import MAX_VOLUME, MIXER_NOISE, NOISE_PERIODS
from generators.generator import Generator
from instructions.noise import NoiseInstruction
from timers.lfsr import LFSRTimer
from typehints.general import Initials


class NoiseGenerator(Generator[NoiseInstruction, LFSRTimer]):
    def __init__(self, config: Config, name: GeneratorName = GeneratorName.NOISE) -> None:
        super().__init__(config, name)
        self.timer = LFSRTimer(
            sample_rate=config.library.sample_rate,
            change_rate=config.library.change_rate,
            reset_phase=config.generation.reset_phase,
        )

    def __call__(
        self,
        noise_instruction: NoiseInstruction,
        initials: Initials = None,
        save: bool = False,
    ) -> np.ndarray:
        initial_lfsr, initial_clock = initials if initials is not None else (None, None)
        self.validate(initial_lfsr, initial_clock)

        if not noise_instruction.on:
            return np.zeros(self.frame_length, dtype=np.float32)

        output = self.generate(noise_instruction, initials=initials)
        self.save_state(save, noise_instruction, initials)

        return output

    def set_timer(self, instruction: NoiseInstruction) -> None:
        if instruction.on:
            self.timer.short = instruction.short
            self.timer.period = instruction.period
        else:
            self.timer.short = False
            self.timer.period = 0

    def apply(self, output: np.ndarray, instruction: NoiseInstruction) -> np.ndarray:
        volume = 0.5 * float(instruction.volume) / float(MAX_VOLUME)
        return volume * output * MIXER_NOISE

    def get_possible_instructions(self) -> List[NoiseInstruction]:
        noise_instructions = [
            NoiseInstruction(
                on=False,
                period=0,
                volume=0,
                short=False,
            )
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

    @staticmethod
    def get_instruction_type() -> type:
        return NoiseInstruction

    @classmethod
    def class_name(cls) -> GeneratorClassName:
        return GeneratorClassName.NOISE_GENERATOR
