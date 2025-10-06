from typing import Any, Optional, Tuple

import numpy as np

from ffts.window import Window


class Timer:
    def __call__(self, window: Optional[Window] = None, **kwargs) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    @property
    def initials(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def prepare_frame(self, window: Optional[Window] = None) -> np.ndarray:
        length = self.frame_length if window is None else window.size
        return np.zeros(length, dtype=np.float32)

    def generate_frame(self) -> np.ndarray:
        raise NotImplementedError("Subclasses must implement this method")

    def generate_window(self, window: Window) -> np.ndarray:
        assert window is not None, "Window must be provided"

        backward_frames = []
        for _ in range(window.backward_frames):
            backward_frames.append(self.generate_frame(False, save=False))

        forward_frames = []
        for _ in range(window.forward_frames):
            forward_frames.append(self.generate_frame(True, save=True))

        frame = np.concatenate([np.concatenate(backward_frames[::-1]), np.concatenate(forward_frames)])
        start = self.frame_length * window.backward_frames + window.left_offset
        end = start + window.size

        return frame[start:end]

    def reset(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def validate(self, *args, **kwargs) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def get(self) -> Tuple[Any, ...]:
        raise NotImplementedError("Subclasses must implement this method")

    def set(self, value: Optional[Tuple[Any, ...]]) -> None:
        raise NotImplementedError("Subclasses must implement this method")
