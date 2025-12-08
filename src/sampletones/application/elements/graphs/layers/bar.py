from dataclasses import dataclass, field

import numpy as np

from sampletones.typehints import Color

from ....constants.graphs import (
    COL_BAR_PLOT,
    VAL_BAR_PLOT_BAR_WEIGHT,
)


@dataclass(frozen=True)
class BarLayer:
    data: np.ndarray
    name: str
    color: Color = COL_BAR_PLOT
    bar_weight: float = VAL_BAR_PLOT_BAR_WEIGHT

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", self.data.astype(np.int64))
        object.__setattr__(self, "x_data", np.arange(len(self.data)).astype(np.float32) + 0.5)
        object.__setattr__(self, "y_data", self.data.tolist())
