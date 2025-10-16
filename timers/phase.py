from typing import Any, Optional, Tuple

import numpy as np

from constants import APU_CLOCK, RESET_PHASE
from generators.types import Initials
from timers.timer import Timer


class PhaseTimer(Timer):
    def __init__(
        self,
        sample_rate: int,
        change_rate: int,
        reset_phase: bool = RESET_PHASE,
        phase_increment: float = 1.0,
    ) -> None:
        super().__init__(sample_rate, change_rate, reset_phase)
        self._cycles_per_sample: float = APU_CLOCK / sample_rate
        self._frequency: float = 0.0
        self._timer: int = 0
        self._timer_ticks: int = 0

        self.phase: float = 0.0

        self.phase_increment: float = phase_increment

    def __call__(
        self,
        initials: Initials = None,
    ) -> np.ndarray:
        (initial_phase,) = initials if initials is not None else (None,)
        self.validate(initial_phase)

        if initial_phase is not None:
            self.phase = initial_phase

        if self._timer_ticks <= 0:
            frame = self.prepare_frame(None)
            frame.fill(self.phase)
            return frame

        return self.generate_frame()

    def calculate_offset(self, initials: Initials = None) -> int:
        phase = initials[0] if initials is not None else 0.0
        return round(self.sample_rate / self._real_frequency * phase)

    def generate_frame(self, direction: bool = True, save: bool = True) -> np.ndarray:
        indices = np.arange(self.frame_length) + 1
        delta = self.phase_increment / self._timer_ticks * self._cycles_per_sample
        direction = 1.0 if direction else -1.0
        lower = np.ceil(1.0 + abs(delta * indices[-1]))
        frame = np.fmod(lower + indices * delta * direction + self.phase, 1.0)

        if save:
            self.phase = float(frame[-1])

        return frame if direction > 0 else frame[::-1]

    @property
    def initials(self) -> Tuple[Any, ...]:
        return (self.phase,)

    @staticmethod
    def frequency_to_timer(frequency: float) -> int:
        if frequency <= 0:
            return 0

        timer = round(APU_CLOCK / (16 * frequency)) - 1
        return max(0, min(timer, 0x7FF))

    @staticmethod
    def timer_to_frequency(timer: int) -> float:
        if timer <= 0:
            return 0.0
        return APU_CLOCK / (16 * (timer + 1))

    @staticmethod
    def get_timer_ticks(timer: int) -> int:
        return (timer + 1) * 16 if timer > 0 else 0

    def round_frequency_by_timer(self) -> None:
        self._frequency = APU_CLOCK / (16 * (self._timer + 1))

    @property
    def frequency(self) -> float:
        return self._frequency

    @property
    def base_length(self) -> int:
        return self._base_length

    @frequency.setter
    def frequency(self, value: float) -> None:
        self._frequency = value
        self._timer = self.frequency_to_timer(value)
        self._timer_ticks = self.get_timer_ticks(self._timer)
        self.round_frequency_by_timer()

        self._real_frequency = self.frequency * self.phase_increment

        if self.reset_phase:
            self.reset()

    def reset(self) -> None:
        self.phase = 0.0

    def validate(self, initial_phase: Optional[float]) -> None:
        if initial_phase is not None:
            if not isinstance(initial_phase, float) or (initial_phase < 0.0 or initial_phase >= 1.0):
                raise ValueError("Initial phase for PhaseTimer must be between 0.0 and 1.0")

    def get(self) -> Tuple[float]:
        return (self.phase,)

    def set(self, value: Optional[Tuple[float]]) -> None:
        if value is None:
            self.reset()
            return

        value = value[0]
        assert isinstance(value, float) and (0.0 <= value < 1.0), "Phase value must be between 0.0 and 1.0"
        self.phase = value
