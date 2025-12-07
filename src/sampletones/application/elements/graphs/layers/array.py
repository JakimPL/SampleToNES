from dataclasses import dataclass, field

import numpy as np

from sampletones.typehints import Color

from ....constants import COL_WAVEFORM_DEFAULT, VAL_WAVEFORM_SAMPLE_THICKNESS


@dataclass(frozen=True)
class ArrayLayer:
    data: np.ndarray
    name: str
    color: Color = COL_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", self.data.astype(np.float32))
        object.__setattr__(self, "x_data", np.arange(len(self.data)).astype(np.float32))
        object.__setattr__(self, "y_data", self.data)
