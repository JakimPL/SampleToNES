from dataclasses import dataclass, field
from typing import Any

import numpy as np

from sampletones.library import InstructionLibraryFragment
from sampletones.typehints import Color

from ....constants.graphs import COL_WAVEFORM_DEFAULT, VAL_WAVEFORM_SAMPLE_THICKNESS


@dataclass(frozen=True)
class WaveformLayer:
    fragment: InstructionLibraryFragment[Any]
    name: str
    color: Color = COL_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        data = self.fragment.data.astype(np.float32)
        object.__setattr__(self, "x_data", np.arange(len(data)).astype(np.float32))
        object.__setattr__(self, "y_data", data)
