from typing import Any, Optional, Tuple

import numpy as np

from ffts.window import Window
from generators.types import Initials


class Timer:
    def __call__(self, window: Optional[Window] = None, **kwargs) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def initials(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def calculate_offset(self, initials: Initials = None) -> int:
        raise NotImplementedError("Subclasses must implement this method")

    def prepare_frame(self, window: Optional[Window] = None) -> np.ndarray:
        length = self.frame_length if window is None else window.size
        return np.zeros(length, dtype=np.float32)

    def generate_sample(self, backward_frames: int, forward_frames: int) -> Tuple[np.ndarray, int]:
        initials = self.get()

        offset = backward_frames * self.frame_length

        self.reset()
        backward_frames = [self.generate_frame(False, save=True) for _ in range(backward_frames)]

        self.reset()
        forward_frames = [self.generate_frame(True, save=True) for _ in range(forward_frames)]

        self.set(initials)

        sample = np.concatenate([np.concatenate(backward_frames[::-1]), np.concatenate(forward_frames)])
        return sample, offset

    def generate_frame(self) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def reset(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def validate(self, *args, **kwargs) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def get(self) -> Initials:
        raise NotImplementedError("Subclasses must implement this method")

    def set(self, value: Initials) -> None:
        raise NotImplementedError("Subclasses must implement this method")
