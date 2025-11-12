from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

from library import LibraryFragment

from ....constants import CLR_WAVEFORM_DEFAULT, VAL_WAVEFORM_SAMPLE_THICKNESS


@dataclass(frozen=True)
class WaveformLayer:
    fragment: LibraryFragment
    name: str
    color: Tuple[int, int, int, int] = CLR_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self):
        data = self.fragment.sample
        object.__setattr__(self, "x_data", np.arange(len(data)))
        object.__setattr__(self, "y_data", data.tolist())
