from types import ModuleType
from typing import Callable, TypeAlias, TypeVar, Union

import numpy as np

from sampletones import xp

T = TypeVar("T")

Integer = Union[int, np.integer, xp.integer]
Float = Union[float, np.floating, xp.floating]
Numeric = Union[Integer, Float]
Array = Union[np.ndarray, xp.ndarray]
ArrayOrScalar = Union[Numeric, Array]

IntegerClasses = (int, np.integer, xp.integer)  # pylint: disable=invalid-name
FloatClasses = (float, np.floating, xp.floating)  # pylint: disable=invalid-name
NumericClasses = IntegerClasses + FloatClasses  # pylint: disable=invalid-name
ArrayClasses = (np.ndarray, xp.ndarray)  # pylint: disable=invalid-name
ArrayOrScalarClasses = NumericClasses + ArrayClasses  # pylint: disable=invalid-name

UnaryTransformation: TypeAlias = Callable[[T], T]
BinaryTransformation: TypeAlias = Callable[[T, T], T]
MultaryTransformation: TypeAlias = Callable[..., T]


def get_array_module(array: Array) -> ModuleType:
    """
    Get the appropriate array module (NumPy or CuPy) based on the input array type.

    Args:
        Input array which can be either a NumPy ndarray or a CuPy ndarray.

    Returns:
        The corresponding array module (np or xp).

    Raises:
        TypeError: If the input array is neither a NumPy ndarray nor a CuPy ndarray
    """
    module: ModuleType
    if isinstance(array, xp.ndarray):
        module = xp

    if isinstance(array, np.ndarray):
        module = np

    else:
        raise TypeError(f"Unsupported array type: {type(array)}")

    return module
