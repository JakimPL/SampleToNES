from typing import Any, Callable, Optional, Tuple, Union

import numpy as np

Initials = Optional[Tuple[Any, ...]]

FeatureValue = Union[int, np.ndarray]

UnaryTransformation = Callable[[np.ndarray], np.ndarray]
BinaryTransformation = Callable[[np.ndarray, np.ndarray], np.ndarray]
MultaryTransformation = Callable[..., np.ndarray]
