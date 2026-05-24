from dataclasses import dataclass

import numpy as np

from sampletones_core.audio import minmax_decimate
from sampletones_shared.types.application import Color

from ....constants.graphs import COL_WAVEFORM_DEFAULT, VAL_MAX_WAVEFORM_DISPLAY_POINTS, VAL_WAVEFORM_SAMPLE_THICKNESS
from .layer import Layer


@dataclass(frozen=True)
class ArrayLayer(Layer):
    data: np.ndarray
    name: str
    color: Color = COL_WAVEFORM_DEFAULT
    line_thickness: float = VAL_WAVEFORM_SAMPLE_THICKNESS

    def __post_init__(self) -> None:
        y_data = self.data.astype(np.float32)
        length = y_data.shape[0]

        assert y_data.ndim == 1, "ArrayLayer data must be a 1D numpy array"
        if length > VAL_MAX_WAVEFORM_DISPLAY_POINTS:
            x_data, y_data = minmax_decimate(y_data, num_buckets=VAL_MAX_WAVEFORM_DISPLAY_POINTS)
        else:
            x_data = np.arange(y_data.shape[0], dtype=np.float32)

        object.__setattr__(self, "x_data", x_data)
        object.__setattr__(self, "y_data", y_data)
