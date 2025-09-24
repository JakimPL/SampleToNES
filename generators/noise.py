from typing import List, Optional

import numpy as np

from constants import APU_CLOCK, MAX_VOLUME, VOLUME_RANGE
from generators.generator import Generator
from instructions.noise import NoiseInstruction

NOISE_PERIODS = [4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068]

MIXER_NOISE = 0.5804935370152762


class NoiseGenerator(Generator):
    def __init__(self, config):
        super().__init__(config)

    def __call__(self, noise_instruction: NoiseInstruction, initial_phase: Optional[int] = None) -> np.ndarray:
        output = np.zeros(self.frames, dtype=np.float32)

        if not noise_instruction.on or noise_instruction.period is None:
            return output

        apu_period = NOISE_PERIODS[noise_instruction.period]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        clocks_per_sample = lfsr_clock_hz / float(self.config.sample_rate)
        lfsr = int(initial_phase) if initial_phase is not None else 1

        clk_acc = 0.0
        vol_scale = float(noise_instruction.volume) / float(MAX_VOLUME)

        for i in range(self.frames):
            clk_acc += clocks_per_sample
            while clk_acc >= 1.0:
                clk_acc -= 1.0
                lfsr = self._clock_lfsr(lfsr, noise_instruction.mode)

            if (lfsr & 1) == 0:
                sample_val = vol_scale
            else:
                sample_val = 0.0

            output[i] = sample_val

        self.timer.phase = int(lfsr)

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
            for mode in [False]:
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
