from dataclasses import dataclass

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_application.utils.palette.color import PaletteColor
from sampletones_core.audio import minmax_decimate


@dataclass(frozen=True)
class ArrayLayer(Layer):
    data: np.ndarray
    name: str
    color: PaletteColor
    max_display_points: int

    def __post_init__(self) -> None:
        y_data = self.data.astype(np.float32)
        length = y_data.shape[0]

        assert y_data.ndim == 1, "ArrayLayer data must be a 1D numpy array"
        if length > self.max_display_points:
            x_data, y_data = minmax_decimate(y_data, num_buckets=self.max_display_points)
        else:
            x_data = np.arange(y_data.shape[0], dtype=np.float32)

        object.__setattr__(self, "x_data", x_data)
        object.__setattr__(self, "y_data", y_data)
