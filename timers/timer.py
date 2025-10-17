from typing import Any, Optional, Tuple

import numpy as np

from constants import RESET_PHASE
from ffts.window import Window
from typehints.general import Initials


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

    def __call__(self, initials: Initials = None) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def initials(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def calculate_offset(self, initials: Initials = None) -> int:
        raise NotImplementedError("Subclasses must implement this method")

    def prepare_frame(self, window: Optional[Window] = None) -> np.ndarray:
        length = self.frame_length if window is None else window.size
        return np.zeros(length, dtype=np.float32)

    def generate_sample(self, window: Window) -> Tuple[np.ndarray, int]:
        base_length = int(np.ceil(max(self.sample_rate / self._real_frequency, window.size)))
        backward_frames = -(-(base_length) // self.frame_length)
        forward_frames = -((-2 * base_length) // self.frame_length)
        return self.generate_frames(backward_frames, forward_frames)

    def generate_window(self, window: Window, initials: Initials = None) -> np.ndarray:
        sample, offset = self.generate_frames(window.backward_frames, window.forward_frames, initials)
        start = offset + window.left_offset
        end = start + window.size
        return sample[start:end] * window.envelope

    def generate_frames(
        self, backward_frames: int, forward_frames: int, initials: Initials = None
    ) -> Tuple[np.ndarray, int]:
        previous_initials = self.get()
        offset = backward_frames * self.frame_length

        self.set(initials)
        frames = [self.generate_frame(False, save=True) for _ in range(backward_frames)][::-1]

        self.set(initials)
        frames.extend([self.generate_frame(True, save=True) for _ in range(forward_frames)])

        self.set(previous_initials)
        sample = np.concatenate(frames)
        return sample, offset

    def generate_frame(self, direction: bool = True, save: bool = True) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def validate(self, *args, **kwargs) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def get(self) -> Initials:
        raise NotImplementedError("Subclasses must implement this method")

    def set(self, value: Initials) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def real_frequency(self) -> float:
        return self._real_frequency
