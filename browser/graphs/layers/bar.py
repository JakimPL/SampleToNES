from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

from constants.browser import CLR_BAR_PLOT_DEFAULT, VAL_BAR_PLOT_BAR_WEIGHT


@dataclass(frozen=True)
class BarLayer:
    data: np.ndarray
    name: str
    color: Tuple[int, int, int, int] = CLR_BAR_PLOT_DEFAULT
    bar_weight: float = VAL_BAR_PLOT_BAR_WEIGHT

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "x_data", np.arange(len(self.data)) + 0.5)
        object.__setattr__(self, "y_data", self.data.tolist())
