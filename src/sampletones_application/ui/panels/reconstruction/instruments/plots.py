from typing import Optional, Tuple

import numpy as np

from sampletones_application.ui.elements.graphs.utils import extend_y_range
from sampletones_application.ui.panels.reconstruction.instruments.config import FeaturePlotConfig
from sampletones_core.features.envelope import Envelope

PlotLimits = Tuple[int, int, Optional[Tuple[int, ...]]]


def plotted_items(envelope: Envelope[int]) -> np.ndarray:
    """The values a dimension writes, as the bar plot draws them."""
    return np.array(envelope.items, dtype=np.int8)


def plot_limits(config: FeaturePlotConfig, data: np.ndarray) -> PlotLimits:
    """The bounds and the ticks one dimension is drawn between.

    A dimension reading around zero takes bounds from the widest value it writes, so an
    envelope describing no frame stands at the floor the empty reading gives it and the
    plot keeps a grid to draw on.
    """
    y_min = config.y_min
    y_max = config.y_max
    y_ticks = config.y_ticks
    if y_min == -1.0 and y_max == -1.0:
        max_abs_value = float(np.max(np.abs(data))) if data.size else 0.0
        y_min = -max_abs_value
        y_max = max_abs_value

        step = max(1, int(np.ceil(max_abs_value / 4)))
        max_tick = step * 4
        y_ticks = tuple(range(-max_tick, max_tick + 1, step))

    y_min, y_max = extend_y_range(y_min, y_max)
    return y_min, y_max, y_ticks
