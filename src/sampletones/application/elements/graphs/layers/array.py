from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

from ....constants import CLR_WAVEFORM_DEFAULT, VAL_WAVEFORM_SAMPLE_THICKNESS


@dataclass(frozen=True)
class ArrayLayer:
    data: np.ndarray
    name: str
    color: Tuple[int, int, int, int] = CLR_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "data", self.data.astype(np.float32))
        object.__setattr__(self, "x_data", np.arange(len(self.data)).astype(np.float32))
        object.__setattr__(self, "y_data", self.data)
