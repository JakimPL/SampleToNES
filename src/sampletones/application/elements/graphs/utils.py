from typing import Tuple

import numpy as np


def extend_y_range(y_min: float, y_max: float) -> Tuple[int, int]:
    gap = max(1.0, y_min * 0.1, y_max * 0.1)
    y_min = int(np.floor(y_min - gap))
    y_max = int(np.ceil(y_max + gap))
    return y_min, y_max
