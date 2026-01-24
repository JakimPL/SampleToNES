from typing import Callable, TypeVar, Union

import numpy as np

from sampletones import xp

T = TypeVar("T")

Integer = Union[int, np.integer, xp.integer]
Float = Union[float, np.floating, xp.floating]
Numeric = Union[Integer, Float]
ArrayOrScalar = Union[Numeric, np.ndarray, xp.ndarray]

UnaryTransformation = Callable[[T], T]
BinaryTransformation = Callable[[T, T], T]
MultaryTransformation = Callable[..., T]
