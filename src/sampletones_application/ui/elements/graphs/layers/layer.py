from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Layer:
    data: Any
    name: str

    x_data: np.ndarray = field(init=False)
    y_data: np.ndarray = field(init=False)
