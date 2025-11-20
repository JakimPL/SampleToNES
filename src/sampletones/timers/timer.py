from typing import Any, Optional, Tuple

import numpy as np

from sampletones.constants.general import (
    MAX_SAMPLE_LENGTH,
    MIN_SAMPLE_LENGTH,
    RESET_PHASE,
)
from sampletones.ffts import CyclicArray, Window
from sampletones.typehints import Initials


class Timer:
    def __init__(
        self,
        sample_rate: int,
        change_rate: int,
        reset_phase: bool = RESET_PHASE,
    ):
        self._real_frequency: float = 0.0
        self.sample_rate: int = sample_rate
        self.reset_phase: bool = reset_phase
        self.change_rate: int = change_rate
        self.frame_length: int = round(self.sample_rate / self.change_rate)

    def __call__(
        self,
        initials: Initials = None,
        save: bool = True,
    ) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def initials(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def calculate_offset(self, initials: Initials = None) -> int:
        raise NotImplementedError("Subclasses must implement this method")

    def prepare_frame(self, window: Optional[Window] = None) -> np.ndarray:
        length = self.frame_length if window is None else window.size
        return np.zeros(length, dtype=np.float32)

    def generate_sample(self) -> CyclicArray:
        min_sample_length = round(MIN_SAMPLE_LENGTH * self.sample_rate)
        max_sample_length = round(MAX_SAMPLE_LENGTH * self.sample_rate)
        base_length = round(self.sample_rate / self._real_frequency)

        if base_length < min_sample_length:
            base_length = int(np.ceil(min_sample_length / base_length)) * base_length

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
        frames = np.concatenate([self.generate_frame(save=True) for _ in range(frames_count)])
        self.set(previous_initials)
        return frames

    def generate_frame(self, save: bool = True) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def validate(self, initials: Initials) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def get(self) -> Initials:
        raise NotImplementedError("Subclasses must implement this method")

    def set(self, value: Initials) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def real_frequency(self) -> float:
        return self._real_frequency
