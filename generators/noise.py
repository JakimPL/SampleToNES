from typing import List, Optional

import numpy as np

from config import Config
from constants import APU_CLOCK, MAX_VOLUME, MIXER_NOISE, NOISE_PERIODS, VOLUME_RANGE
from generators.generator import Generator
from instructions.noise import NoiseInstruction


class NoiseGenerator(Generator):
    def __init__(self, name: str, config: Config) -> None:
        super().__init__(name, config)
        self.timer.phase = 1
        self.clock = 0.0

    def __call__(
        self,
        noise_instruction: NoiseInstruction,
        initial_phase: Optional[int] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        self.validate_initials(initial_phase, initial_clock)
        output = np.zeros(self.frame_length, dtype=np.float32)

        if not noise_instruction.on or noise_instruction.period is None:
            return output

        apu_period = NOISE_PERIODS[noise_instruction.period]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        clocks_per_sample = 2.0 * lfsr_clock_hz / float(self.config.sample_rate)
        vol_scale = 0.5 * float(noise_instruction.volume) / float(MAX_VOLUME)

        if (
            self.previous_instruction
            and self.previous_instruction.on
            and self.previous_instruction.period != noise_instruction.period
        ):
            lfsr = 1
            self.clock = 0.0
        else:
            lfsr = int(initial_phase) if initial_phase is not None else 1
            self.clock = 0.0 if initial_clock is None else initial_clock

        previous_bits = [lfsr & 1]
        for i in range(self.frame_length):
            if previous_bits:
                sample_value = 2.0 * np.mean(previous_bits) - 1.0
                sample_val = sample_value * vol_scale
                output[i] = sample_val
                previous_bits = []
            else:
                output[i] = vol_scale if lfsr & 1 else -vol_scale

            self.clock += clocks_per_sample
            while self.clock >= 1.0:
                self.clock -= 1.0
                lfsr = self._clock_lfsr(lfsr, noise_instruction.mode)
                previous_bits.append(lfsr & 1)

        self.timer.phase = lfsr

        return output * MIXER_NOISE

    def _clock_lfsr(self, lfsr: int, short_mode: bool) -> int:
        bit0 = lfsr & 1
        bitX = (lfsr >> (6 if short_mode else 1)) & 1
        feedback = bit0 ^ bitX
        lfsr = (lfsr >> 1) | (feedback << 14)
        lfsr &= 0x7FFF
        return lfsr

    def get_possible_instructions(self) -> List[NoiseInstruction]:
        noise_instructions = [
            NoiseInstruction(
                on=False,
                period=None,
                volume=0,
                mode=False,
            )
        ]

        for volume in VOLUME_RANGE:
            if volume == 0:
                continue
            for mode in [False, True]:
                for period in range(len(NOISE_PERIODS)):
                    noise_instructions.append(
                        NoiseInstruction(
                            on=True,
                            period=period,
                            volume=volume,
                            mode=mode,
                        )
                    )

        return noise_instructions

    def validate_initials(self, initial_phase: Optional[int], initial_clock: Optional[float]) -> None:
        if initial_phase is not None:
            if not isinstance(initial_phase, int) or (initial_phase < 1 or initial_phase > 0x7FFF):
                raise ValueError("Initial phase for NoiseGenerator must be between 1 and 0x7FFF")

        if initial_clock is not None:
            if not isinstance(initial_clock, float) or (initial_clock < 0.0 or initial_clock > 1.0):
                raise ValueError("Initial clock for NoiseGenerator must be between 0.0 and 1.0")
