from types import ModuleType
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


def get_array_module(array: Array) -> ModuleType:
    """
    Get the appropriate array module (NumPy or CuPy) based on the input array type.

    Args:
        array (Array): Input array which can be either a NumPy ndarray or a CuPy ndarray.

    Returns:
        xp.Module: The corresponding array module (np or xp).
    """
    if isinstance(array, xp.ndarray):
        return xp

    return np
