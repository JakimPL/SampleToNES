from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple, Union

import numpy as np

from constants import APU_CLOCK, NOISE_PERIODS, RESET_PHASE
from timers.timer import Timer


@dataclass(frozen=True)
class LFSRDirection:
    direction: bool
    frame_range: range
    delta: float
    comparison: Callable[[float], bool]
    adjustment: float
    function: Callable

    @classmethod
    def create(cls, lfsr_timer: "LFSRTimer", frame_length: int, direction: bool) -> "LFSRDirection":
        frame_range = range(frame_length) if direction else range(frame_length - 1, -1, -1)
        delta = lfsr_timer.clocks_per_sample if direction else -lfsr_timer.clocks_per_sample
        lfsr_function = lfsr_timer.forward if direction else lfsr_timer.backward
        clock_adjustment = -1.0 if direction else 1.0
        clock_threshold = 1.0 if direction else 0.0
        clock_comparison = (
            (lambda clock: clock >= clock_threshold) if direction else (lambda clock: clock < clock_threshold)
        )

        return cls(
            direction=direction,
            frame_range=frame_range,
            delta=delta,
            function=lfsr_function,
            comparison=clock_comparison,
            adjustment=clock_adjustment,
        )


class LFSRTimer(Timer):
    def __init__(self, sample_rate: int, reset_phase: bool = RESET_PHASE) -> None:
        self._period: int = 0
        self._clock_rate: float = 0.0
        self._clocks_per_sample: float = 0.0
        self.mode: bool = False

        self.lfsr: int = 1
        self.clock: float = 0.0

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

        previous_bits = [self.lfsr & 1]
        lfsr_direction = LFSRDirection.create(self, length, direction)
        for i in lfsr_direction.frame_range:
            frame[i] = self.step(lfsr_direction, previous_bits)

        return frame

    def step(self, lfsr_direction: LFSRDirection, previous_bits: List[int]) -> float:
        if previous_bits:
            value = 2.0 * np.mean(previous_bits) - 1.0
            previous_bits = []
        else:
            value = self.lfsr & 1

        self.clock += lfsr_direction.delta

        while lfsr_direction.comparison(self.clock):
            self.clock += lfsr_direction.adjustment
            self.lfsr = lfsr_direction.function(self.lfsr, self.mode)
            previous_bits.append(self.lfsr & 1)

        return float(value)

    @property
    def initials(self) -> Tuple[Any, ...]:
        return self.lfsr, self.clock

    @property
    def period(self) -> int:
        return self._period

    @period.setter
    def period(self, value: int) -> None:
        apu_period = NOISE_PERIODS[value]
        lfsr_clock_hz = APU_CLOCK / float(apu_period)
        self.clocks_per_sample = 2.0 * lfsr_clock_hz / float(self.sample_rate)
        if self.reset_phase:
            self.reset()

    def forward(self, lfsr: int, short_mode: bool) -> int:
        bit0 = lfsr & 1
        bitX = (lfsr >> (6 if short_mode else 1)) & 1
        feedback = bit0 ^ bitX
        lfsr = (lfsr >> 1) | (feedback << 14)
        lfsr &= 0x7FFF
        return lfsr

    def backward(self, lfsr: int, short_mode: bool) -> int:
        msb = (lfsr >> 14) & 1
        partial = (lfsr & 0x3FFF) << 1
        bitX = (partial >> (6 if short_mode else 1)) & 1
        bit0 = msb ^ bitX
        lfsr = partial | bit0
        lfsr &= 0x7FFF
        return lfsr

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
