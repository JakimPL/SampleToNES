from dataclasses import dataclass
from functools import cached_property
from typing import Tuple

import numpy as np

from sampletones_core.structures.histogram import Histogram


@dataclass(frozen=True)
class StackedFeature:
    """A frame's reading by several spectrum methods, their bins stacked in order.

    Every step of the search reads a frame bin by bin, so the bins of several methods stand in one
    feature, each method's bins after the one before it.

    Attributes:
        layers: Each method's histogram of the frame, the library's method first.
    """

    layers: Tuple[Histogram, ...]

    @cached_property
    def values(self) -> np.ndarray:
        """Every method's values, one method after another."""
        return np.concatenate([np.asarray(layer.values) for layer in self.layers])
