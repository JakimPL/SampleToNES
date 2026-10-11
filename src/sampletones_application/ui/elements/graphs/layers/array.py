from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_core.audio import minmax_decimate


@dataclass(frozen=True)
class ArrayLayer(Layer):
    """A waveform drawn as a line, reduced to the points the display shows.

    Attributes:
        data: The waveform, one-dimensional.
        name: The name the series is labeled by.
        color: The color the line is drawn in.
        max_display_points: How many points the display shows at most.
        points: The positions and values already reduced for ``data``, where a display keeps them;
            left out, the layer reduces ``data`` itself.
    """

    data: np.ndarray
    name: str
    color: BaseColor
    max_display_points: int
    points: Optional[Tuple[np.ndarray, np.ndarray]] = None

    def __post_init__(self) -> None:
        if self.points is not None:
            x_data, y_data = self.points
        else:
            y_data = self.data.astype(np.float32, copy=False)
            assert y_data.ndim == 1, "ArrayLayer data must be a 1D numpy array"
            if y_data.shape[0] > self.max_display_points:
                x_data, y_data = minmax_decimate(y_data, num_buckets=self.max_display_points)
            else:
                x_data = np.arange(y_data.shape[0], dtype=np.float32)

        object.__setattr__(self, "x_data", x_data)
        object.__setattr__(self, "y_data", y_data)
