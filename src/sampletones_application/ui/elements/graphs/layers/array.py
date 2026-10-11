from dataclasses import dataclass
from typing import Tuple

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_application.utils.palette.colors.base import BaseColor


@dataclass(frozen=True)
class ArrayLayer(Layer):
    """A waveform drawn as a line, at the points the display reduced it to.

    Attributes:
        data: The waveform, one-dimensional.
        name: The name the series is labeled by.
        color: The color the line is drawn in.
        points: The positions and values ``data`` was reduced to for the display.
    """

    data: np.ndarray
    name: str
    color: BaseColor
    points: Tuple[np.ndarray, np.ndarray]

    def __post_init__(self) -> None:
        x_data, y_data = self.points
        object.__setattr__(self, "x_data", x_data)
        object.__setattr__(self, "y_data", y_data)
