from dataclasses import dataclass

import numpy as np

from sampletones.types.application import Color

from ....constants.graphs import COL_BAR_PLOT, VAL_BAR_PLOT_BAR_WEIGHT
from .layer import Layer


@dataclass(frozen=True)
class BarLayer(Layer):
    data: np.ndarray
    name: str
    color: Color = COL_BAR_PLOT
    bar_weight: float = VAL_BAR_PLOT_BAR_WEIGHT

    def __post_init__(self) -> None:
        data = self.data.astype(np.int64)
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "x_data", np.arange(len(self.data)).astype(np.float32) + 0.5)
        object.__setattr__(self, "y_data", np.array(data, dtype=np.float32))
