from typing import List, Optional

import numpy as np

from config import Config
from constants import MAX_VOLUME, MIXER_NOISE, NOISE_PERIODS
from ffts.window import Window
from generators.generator import Generator
from generators.types import Initials
from instructions.noise import NoiseInstruction
from timers.lfsr import LFSRTimer


class NoiseGenerator(Generator):
    def __init__(self, config: Config, name: str = "noise") -> None:
        super().__init__(config, name)
        self.timer = LFSRTimer(
            sample_rate=config.sample_rate, change_rate=config.change_rate, reset_phase=config.reset_phase
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

        return output * MIXER_NOISE * self.config.mixer

    def set_timer(self, noise_instruction: NoiseInstruction) -> None:
        if noise_instruction.on:
            self.timer.mode = noise_instruction.mode
            self.timer.period = noise_instruction.period
        else:
            self.timer.mode = False
            self.timer.period = 0

    def apply(self, output: np.ndarray, noise_instruction: NoiseInstruction) -> np.ndarray:
        volume = 0.5 * float(noise_instruction.volume) / float(MAX_VOLUME)
        return volume * output

    def get_possible_instructions(self) -> List[NoiseInstruction]:
        noise_instructions = [
            NoiseInstruction(
                on=False,
                period=None,
                volume=0,
                mode=False,
            )
        ]

        for period in range(len(NOISE_PERIODS)):
            for volume in range(1, MAX_VOLUME + 1):
                for mode in [False, True]:
                    noise_instructions.append(
                        NoiseInstruction(
                            on=True,
                            period=period,
                            volume=volume,
                            mode=mode,
                        )
                    )

        return noise_instructions

    @staticmethod
    def get_instruction_type() -> type:
        return NoiseInstruction

    @classmethod
    def class_name(cls) -> str:
        return cls.__name__
