from dataclasses import dataclass, field

import numpy as np

from sampletones_application.ui.elements.graphs.layers.layer import Layer
from sampletones_shared.types.application import Color

_DEFAULT_COLOR: Color = (100, 200, 255, 255)
_DEFAULT_BAR_WEIGHT: float = 0.8


@dataclass(frozen=True)
class BarLayer(Layer):
    data: np.ndarray
    name: str
    color: Color = field(default_factory=lambda: _DEFAULT_COLOR)
    bar_weight: float = _DEFAULT_BAR_WEIGHT

    def __post_init__(self) -> None:
        data = self.data.astype(np.int64)
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "x_data", np.arange(len(self.data)).astype(np.float32) + 0.5)
        object.__setattr__(self, "y_data", np.array(data, dtype=np.float32))
