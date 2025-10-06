from typing import Any, List, Optional, Tuple

import numpy as np

from config import Config
from constants import MAX_VOLUME, MIXER_NOISE, NOISE_PERIODS
from generators.generator import Generator
from instructions.noise import NoiseInstruction
from timers.lfsr import LFSRTimer


class NoiseGenerator(Generator):
    def __init__(self, name: str, config: Config) -> None:
        super().__init__(name, config)
        self.timer = LFSRTimer(
            sample_rate=config.sample_rate, change_rate=config.change_rate, reset_phase=config.reset_phase
        )

    def __call__(
        self,
        noise_instruction: NoiseInstruction,
        initials: Optional[Tuple[Any, ...]] = None,
        length: Optional[int] = None,
        direction: bool = True,
        save: bool = False,
    ) -> np.ndarray:
        initial_lfsr, initial_clock = initials if initials is not None else (None, None)
        self.validate(initial_lfsr, initial_clock)
        frame_length = self.frame_length if length is None else length
        output = np.zeros(frame_length, dtype=np.float32)

        if not noise_instruction.on:
            return output

        self.timer.mode = noise_instruction.mode
        self.timer.period = noise_instruction.period
        volume = 0.5 * float(noise_instruction.volume) / float(MAX_VOLUME)

        output = volume * self.timer(
            frame_length,
            direction=direction,
            initial_lfsr=initial_lfsr,
            initial_clock=initial_clock,
        )

        if not save:
            self.timer.set(initials)
        else:
            self.previous_instruction = noise_instruction

        return output * MIXER_NOISE

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
