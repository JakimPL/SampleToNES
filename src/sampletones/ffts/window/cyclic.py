from types import ModuleType
from typing import Optional, Union

import numpy as np
from pydantic import ConfigDict, Field

from sampletones.constants.general import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones.data import DataModel

from .window import Window


class CyclicArray(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    array: np.ndarray
    sample_rate: int = Field(
        ...,
        gt=MIN_SAMPLE_RATE,
        lt=MAX_SAMPLE_RATE,
        description="Sample rate of the audio data in Hz.",
        frozen=True,
    )
    frequency: float = Field(
        default=0.0,
        description="Frequency of the cyclic array in Hz.",
        frozen=True,
    )

    def get_offset(self, phase: float) -> int:
        assert isinstance(phase, float), "Phase must be a float value between 0.0 and 1.0."
        assert 0.0 <= phase < 1.0, "Phase must be in the range [0.0, 1.0)."
        if self.frequency <= 0.0:
            return 0

        return round((phase * self.sample_rate) / self.frequency)

    def get_fragment(self, phase: Union[int, float] = 0, length: Optional[int] = None) -> np.ndarray:
        n = len(self.array)
        if n == 0:
            return np.empty(0, dtype=self.array.dtype)

        if length is None:
            length = n

        offset = self.get_offset(phase) if isinstance(phase, float) else phase
        idx = np.arange(offset, offset + length) % n
        return self.array[idx]

    def get_window(self, phase: Union[int, float], window: Window) -> np.ndarray:
        offset = self.get_offset(phase) if isinstance(phase, float) else phase
        offset += window.left_offset
        fragment = self.get_fragment(offset, window.size)
        return fragment * window.envelope

    @property
    def length(self) -> int:
        return len(self.array)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.arrays.CyclicArray as FBCyclicArray

        return FBCyclicArray

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.arrays.CyclicArray as FBCyclicArray

        return FBCyclicArray.CyclicArray
