from typing import Optional, Union

import numpy as np

from constants import APU_CLOCK, RESET_PHASE, SAMPLE_RATE


class Timer:
    def __init__(self, sample_rate: int = SAMPLE_RATE, reset_phase: bool = RESET_PHASE) -> None:
        self._frequency = 0.0
        self._timer = 0
        self._timer_ticks = 0

        self.phase = 0.0
        self.sample_rate = sample_rate
        self.cycles_per_sample = APU_CLOCK / sample_rate
        self.reset_phase = reset_phase

    def __call__(
        self,
        frames: Union[int, np.ndarray],
        initial_phase: Optional[Union[float, int]] = None,
    ) -> np.ndarray:
        if isinstance(frames, int):
            frames = np.zeros(frames, dtype=np.float32)
        elif not isinstance(frames, np.ndarray):
            raise TypeError("'frames' must be an int or a numpy array")

        if initial_phase is not None:
            self.phase = initial_phase

        for i in range(len(frames)):
            frames[i] = self.step()

        return frames

    @staticmethod
    def frequency_to_timer(frequency: float) -> int:
        if frequency <= 0:
            return 0

        timer = round(APU_CLOCK / (16 * frequency)) - 1
        return max(0, min(timer, 0x7FF))

    @staticmethod
    def get_timer_ticks(timer: int) -> int:
        return (timer + 1) * 16 if timer > 0 else 0

    def round_frequency_by_timer(self) -> None:
        self._frequency = APU_CLOCK / (16 * (self._timer + 1))

    @property
    def frequency(self) -> float:
        return self._frequency

    @frequency.setter
    def frequency(self, value: float) -> None:
        self._frequency = value
        self._timer = self.frequency_to_timer(value)
        self._timer_ticks = self.get_timer_ticks(self._timer)
        self.round_frequency_by_timer()
        if self.reset_phase:
            self.phase = 0.0

    def step(self) -> float:
        if self._timer_ticks > 0:
            self.phase += 1.0 / self._timer_ticks * self.cycles_per_sample
            if self.phase >= 1.0:
                self.phase -= 1.0

        return self.phase
