from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Union

import numpy as np

from constants import APU_CLOCK, RESET_PHASE
from timers.timer import Timer


@dataclass(frozen=True)
class PhaseDirection:
    direction: bool
    frame_range: range
    delta: float
    comparison: Callable[[float], bool]
    adjustment: float

    @classmethod
    def create(cls, phase_timer: "PhaseTimer", frame_length: int, direction: bool) -> "PhaseDirection":
        frame_range = range(frame_length) if direction else range(frame_length - 1, -1, -1)
        base_delta = phase_timer.phase_increment / phase_timer._timer_ticks * phase_timer.cycles_per_sample
        delta = base_delta if direction else -base_delta
        phase_threshold = 1.0 if direction else 0.0
        phase_adjustment = -1.0 if direction else 1.0
        phase_comparison = (
            (lambda phase: phase >= phase_threshold) if direction else (lambda phase: phase < phase_threshold)
        )

        return cls(
            direction=direction,
            frame_range=frame_range,
            delta=delta,
            comparison=phase_comparison,
            adjustment=phase_adjustment,
        )


class PhaseTimer(Timer):
    def __init__(
        self,
        sample_rate: int,
        reset_phase: bool = RESET_PHASE,
        phase_increment: float = 1.0,
    ) -> None:
        self._frequency: float = 0.0
        self._timer: int = 0
        self._timer_ticks: int = 0

        self.phase: float = 0.0
        self.cycles_per_sample: float = APU_CLOCK / sample_rate

        self.sample_rate: int = sample_rate
        self.reset_phase: bool = reset_phase
        self.phase_increment: float = phase_increment

    def __call__(
        self,
        length: Union[int, np.ndarray],
        direction: bool = True,
        initial_phase: Optional[Union[float, int]] = None,
    ) -> np.ndarray:
        frame = self.prepare_frame(length)

        if initial_phase is not None:
            self.phase = initial_phase

        phase_direction = PhaseDirection.create(self, length, direction)
        for i in phase_direction.frame_range:
            frame[i] = self.step(phase_direction)

        return frame

    def step(self, phase_direction: PhaseDirection) -> float:
        if self._timer_ticks > 0:
            self.phase += phase_direction.delta
            if phase_direction.comparison(self.phase):
                self.phase += phase_direction.adjustment

        return self.phase

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

    @frequency.setter
    def frequency(self, value: float) -> None:
        self._frequency = value
        self._timer = self.frequency_to_timer(value)
        self._timer_ticks = self.get_timer_ticks(self._timer)
        self.round_frequency_by_timer()
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
