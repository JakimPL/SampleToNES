from typing import Tuple

import numpy as np
from pydantic import BaseModel

from browser.constants import CLR_WAVEFORM_DEFAULT as WAVEFORM_DEFAULT_COLOR


class WaveformLayer(BaseModel):
    name: str
    data: np.ndarray
    color: Tuple[int, int, int, int] = WAVEFORM_DEFAULT_COLOR
    visible: bool = True
    line_thickness: float = 1.0

    class Config:
        arbitrary_types_allowed = True
        frozen = True
