from typing import Union

import numpy as np

from sampletones.ffts.window import Window


class CyclicArray:
    array: np.ndarray
    sample_rate: int
    frequency: float = 0.0

    def get_offset(self, phase: Union[int, float]) -> int:
        return round((phase * self.sample_rate) / self.frequency)

    def get_fragment(self, phase: Union[int, float], length: int) -> np.ndarray:
        n = len(self.array)
        if n == 0:
            return np.empty(0, dtype=self.array.dtype)

        offset = self.get_offset(phase) if isinstance(phase, float) else phase
        idx = np.arange(offset, offset + length) % n
        return self.array[idx]

    def get_window(self, phase: Union[int, float], window: Window) -> np.ndarray:
        offset = self.get_offset(phase) if isinstance(phase, float) else phase
        offset += window.left_offset
        fragment = self.get_fragment(offset, window.size)
        return fragment * window.envelope
