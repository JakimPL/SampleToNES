from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from constants import APU_CLOCK, NOISE_PERIODS, RESET_PHASE
from timers.timer import Timer


class LFSRTimer(Timer):
    def __init__(self, sample_rate: int, reset_phase: bool = RESET_PHASE) -> None:
        self._clocks_per_sample: float = 0.0
        self.mode: bool = False

        self.lfsr: int = 1
        self.clock: float = 0.0
        self.previous_bits: List[int] = [1]

        self.sample_rate: int = sample_rate
        self.reset_phase: bool = reset_phase

    def __call__(
        self,
        length: Union[int, np.ndarray],
        direction: bool = True,
        initial_lfsr: Optional[int] = None,
        initial_clock: Optional[float] = None,
    ) -> np.ndarray:
        frame = self.prepare_frame(length)

        if initial_lfsr is not None:
            self.lfsr = initial_lfsr

        if initial_clock is not None:
            self.clock = initial_clock

        if self._clocks_per_sample <= 0:
            frame.fill(2.0 * (self.lfsr & 1) - 1.0)
            return frame

        function = self.forward if direction else self.backward
        indices = np.arange(len(frame) + 1)
        direction = 1.0 if direction else -1.0
        delta = self._clocks_per_sample * direction
        clock = indices * delta + self.clock
        changes = np.diff(np.floor(clock)).astype(int)

        for i in range(len(frame)):
            count = abs(changes[i])
            if count == 0:
                frame[i] = self.lfsr & 1
            elif count == 1:
                frame[i] = function() & 1
            else:
                bit_sum = 0
                for _ in range(count):
                    bit_sum += function() & 1

                frame[i] = bit_sum / count

        self.clock = float(clock[-1] % 1.0)
        frame = 2.0 * frame - 1.0
        return frame[::-1] if direction < 0 else frame

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.lfsr, self.clock

    @property
    def period(self) -> int:
        return self._period

    @period.setter
    def period(self, value: int) -> None:
        self._period = value
        apu_period = NOISE_PERIODS[value]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        self._clocks_per_sample = 2.0 * lfsr_clock_hz / float(self.sample_rate)
        if self.reset_phase:
            self.reset()

    def forward(self) -> int:
        bit0 = self.lfsr & 1
        bitX = (self.lfsr >> (6 if self.mode else 1)) & 1
        feedback = bit0 ^ bitX
        self.lfsr = (self.lfsr >> 1) | (feedback << 14)
        self.lfsr &= 0x7FFF
        return self.lfsr

    def backward(self) -> int:
        msb = (self.lfsr >> 14) & 1
        partial = (self.lfsr & 0x3FFF) << 1
        bitX = (partial >> (6 if self.mode else 1)) & 1
        bit0 = msb ^ bitX
        self.lfsr = partial | bit0
        self.lfsr &= 0x7FFF
        return self.lfsr

    def reset(self) -> None:
        self.lfsr = 1
        self.clock = 0.0

    def validate(self, initial_lfsr: Optional[int], initial_clock: Optional[float]) -> None:
        if initial_lfsr is not None:
            if not isinstance(initial_lfsr, int) or (initial_lfsr < 1 or initial_lfsr > 0x7FFF):
                raise ValueError(f"Initial LFSR for LFSRTimer must be between 1 and 0x7FFF")

        if initial_clock is not None:
            if not isinstance(initial_clock, float) or (initial_clock < 0.0 or initial_clock >= 1.0):
                raise ValueError(f"Initial clock for LFSRTimer must be between 0.0 and 1.0")

    def get(self) -> Tuple[int, float]:
        return self.lfsr, self.clock

    def set(self, value: Optional[Tuple[int, float]]) -> None:
        if value is None:
            self.reset()
            return

        lfsr, clock = value
        assert isinstance(lfsr, int) and (1 <= lfsr <= 0x7FFF), "LFSR value must be between 1 and 0x7FFF"
        assert isinstance(clock, float) and (0.0 <= clock < 1.0), "Clock value must be between 0.0 and 1.0"
        self.lfsr = lfsr
        self.clock = clock
