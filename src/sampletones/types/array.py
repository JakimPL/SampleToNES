from typing import Callable, TypeVar, Union

import numpy as np

from sampletones import xp

T = TypeVar("T")

Integer = Union[int, np.integer, xp.integer]
Float = Union[float, np.floating, xp.floating]
Numeric = Union[Integer, Float]
Array = Union[np.ndarray, xp.ndarray]
ArrayOrScalar = Union[Numeric, Array]

UnaryTransformation = Callable[[T], T]
BinaryTransformation = Callable[[T, T], T]
MultaryTransformation = Callable[..., T]
