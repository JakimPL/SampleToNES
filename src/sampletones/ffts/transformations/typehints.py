from typing import Callable

import numpy as np

UnaryTransformation = Callable[[np.ndarray], np.ndarray]
BinaryTransformation = Callable[[np.ndarray, np.ndarray], np.ndarray]
MultaryTransformation = Callable[..., np.ndarray]
