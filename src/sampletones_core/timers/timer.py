from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import numpy as np

from sampletones_core.constants.algorithm import MAX_SAMPLE_LENGTH, MIN_SAMPLE_LENGTH, RESET_PHASE
from sampletones_core.fft import CyclicArray, Window
from sampletones_shared.types.data import Initials


class Timer(ABC):
    def __init__(
        self,
        sample_rate: int,
        nes_frequency: int,
        reset_phase: bool = RESET_PHASE,
    ):
        self._real_frequency: float = 0.0
        self.sample_rate: int = sample_rate
        self.reset_phase: bool = reset_phase
        self.nes_frequency: int = nes_frequency
        self.frame_length: int = round(self.sample_rate / self.nes_frequency)

    @abstractmethod
    def __call__(
        self,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray: ...

    @property
    @abstractmethod
    def initials(self) -> Tuple[Any, ...]: ...

    @abstractmethod
    def calculate_offset(self, initials: Initials = None) -> int: ...

    def prepare_frame(self, window: Optional[Window] = None) -> np.ndarray:
        length = self.frame_length if window is None else window.size
        return np.zeros(length, dtype=np.float32)

    def calculate_base_length(self, minimum_length: int) -> int:
        """Length in samples of the shortest whole number of wave cycles reaching a minimum.

        Rounding once, after multiplying by the cycle count, keeps the loop point within half
        a sample of a true cycle boundary however many cycles the sample spans.

        Args:
            minimum_length: The shortest acceptable length in samples.

        Returns:
            int: The sample length spanning a whole number of cycles.
        """
        cycle_length = self.sample_rate / self._real_frequency
        cycles = int(np.ceil(minimum_length / cycle_length))
        return round(cycles * cycle_length)

    def generate_sample(self) -> CyclicArray:
        min_sample_length = round(MIN_SAMPLE_LENGTH * self.sample_rate)
        max_sample_length = round(MAX_SAMPLE_LENGTH * self.sample_rate)
        base_length = self.calculate_base_length(min_sample_length)

        frames_count = int(np.ceil(base_length / self.frame_length))
        frames = self.generate_frames(frames_count)[:base_length]

        if frames.shape[0] > max_sample_length:
            start = (frames.shape[0] - max_sample_length) // 2
            end = start + max_sample_length
            frames = frames[start:end]

        return CyclicArray(
            array=frames,
            sample_rate=self.sample_rate,
            frequency=self._real_frequency,
        )

    def generate_frames(
        self,
        frames_count: int,
        initials: Initials = None,
    ) -> np.ndarray:
        previous_initials = self.get()
        self.set(initials)
        frames: np.ndarray = np.concatenate([self.generate_frame(save=True) for _ in range(frames_count)])
        self.set(previous_initials)
        return frames

    @abstractmethod
    def generate_frame(self, save: bool = True) -> np.ndarray: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def validate(self, initials: Initials) -> None: ...

    @abstractmethod
    def get(self) -> Initials: ...

    @abstractmethod
    def set(self, value: Initials) -> None: ...

    @property
    def real_frequency(self) -> float:
        return self._real_frequency
