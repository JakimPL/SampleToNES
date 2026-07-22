from types import ModuleType
from typing import Callable, TypeAlias, TypeVar, Union

import numpy as np
import numpy.typing as np_typing

from sampletones_shared.array import xp, xp_typing

T = TypeVar("T")

Integer = Union[bool, int, np.integer, xp.integer]
Float = Union[float, np.floating, xp.floating]
Numeric = Union[Integer, Float]
Array = Union[np.ndarray, xp.ndarray]
ArrayOrNumeric = Union[Numeric, Array]

IntegerClasses = (int, np.integer, xp.integer)  # pylint: disable=invalid-name
FloatClasses = (float, np.floating, xp.floating)  # pylint: disable=invalid-name
NumericClasses = IntegerClasses + FloatClasses  # pylint: disable=invalid-name
ArrayClasses = (np.ndarray, xp.ndarray)  # pylint: disable=invalid-name
ArrayOrScalarClasses = NumericClasses + ArrayClasses  # pylint: disable=invalid-name

DTypeLike = Union[np_typing.DTypeLike, xp_typing.DTypeLike]

UnaryTransformation: TypeAlias = Callable[[T], T]
BinaryTransformation: TypeAlias = Callable[[T, T], T]
MultaryTransformation: TypeAlias = Callable[..., T]


def get_array_module(array: Array) -> ModuleType:
    """
    Gets the array module (NumPy or CuPy) matching the input array type.

    A CuPy ndarray resolves to the CuPy module; every other value resolves to NumPy.

    Args:
        array: Input array, either a NumPy ndarray or a CuPy ndarray.

    Returns:
        The corresponding array module (np or xp).
    """
    module: ModuleType
    if isinstance(array, xp.ndarray):
        module = xp
    else:
        module = np

    return module
