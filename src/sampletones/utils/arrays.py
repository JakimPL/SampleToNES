from typing import Any, Optional, Union, overload

import numpy as np

from sampletones import xp
from sampletones.types.array import (
    Array,
    ArrayClasses,
    ArrayOrNumeric,
    ArrayOrScalarClasses,
    DTypeLike,
    Float,
    Integer,
    IntegerClasses,
    Numeric,
    NumericClasses,
    get_array_module,
)


@overload
def clamp(
    value: Integer,
    min_value: Optional[Integer] = None,
    max_value: Optional[Integer] = None,
) -> int: ...


@overload
def clamp(
    value: Float,
    min_value: Optional[Float] = None,
    max_value: Optional[Float] = None,
) -> float: ...


def clamp(
    value: Numeric,
    min_value: Optional[Numeric] = None,
    max_value: Optional[Numeric] = None,
) -> Union[int, float]:
    """
    Restricts a value to be within a specified range.
    Maximum takes precedence over minimum if
    `max_value` is less than `min_value`, that is the lower value is chosen.

    In case of mixed types among `value`, `min_value`, and `max_value`,
    the function promotes all to float for comparison and returns a float.

    Bounds that are None or NaN are ignored.

    Args:
        value: The value to clamp.
        min_value: The minimum allowed value. Optional.
        max_value: The maximum allowed value. Optional.

    Returns:
        The clamped value. If value is an integer type, returns int.
        If value is a floating point type, returns float.

    Raises:
        TypeError: If value, `min_value`, or `max_value` are of unsupported types.

    Examples:
        >>> clamp(5, 0, 10)
        5
        >>> clamp(-5.0, 1.0, 10.0)
        1.0
        >>> clamp(1, 2)
        2
        >>> clamp(1, max_value=0)
        0
        >>> clamp(1.0, 0.0, float("-inf"))  # max_value takes precedence
        -inf
    """
    if not isinstance(value, NumericClasses):
        raise TypeError(f"Value must be a numeric type, got {type(value)}")

    if min_value is not None and not isinstance(min_value, NumericClasses):
        raise TypeError(f"Unsupported type for min_value: {type(min_value)}")

    if max_value is not None and not isinstance(max_value, NumericClasses):
        raise TypeError(f"Unsupported type for max_value: {type(max_value)}")

    all_integers = all(isinstance(v, IntegerClasses) for v in (value, min_value, max_value) if v is not None)

    if all_integers:
        min_value = int(min_value) if min_value is not None else None
        max_value = int(max_value) if max_value is not None else None
        value = int(value)
    else:
        min_value = float(min_value) if min_value is not None else None
        max_value = float(max_value) if max_value is not None else None
        value = float(value)

    if min_value is not None:
        value = max(value, min_value)

    if max_value is not None:
        value = min(value, max_value)

    return value


def isfinite(value: Optional[ArrayOrNumeric]) -> bool:
    """
    Checks if a numeric value is finite (not NaN or infinite).
    If the value is None, it is considered not finite.

    If the argument is an array, checks if all elements are finite recursively.

    Args:
        value: The numeric value to check.

    Returns:
        True if the value is finite, False if it is NaN, infinite, or None.

    Raises:
        TypeError: If the value is not a numeric nor array type or `None`.
    """
    if value is None:
        return False

    if isinstance(value, ArrayClasses):
        return all(isfinite(v) for v in value)

    if not isinstance(value, NumericClasses):
        raise TypeError(f"Value must be a numeric type or None, got {type(value)}")

    module = get_array_module(value)
    finite: bool = bool(module.isfinite(value))
    return finite


def isnan(value: Optional[ArrayOrNumeric]) -> bool:
    """
    Checks if a numeric value is NaN (Not a Number).

    If the argument is an array, checks if all elements are NaN recursively.

    Args:
        value: The numeric value to check.

    Returns:
        True if the value is `None` or NaN, False otherwise.

    Raises:
        TypeError: If the value is not a numeric type or `None`.
    """
    if value is None:
        return True

    if isinstance(value, ArrayClasses):
        return all(isnan(v) for v in value)

    if not isinstance(value, NumericClasses):
        raise TypeError(f"Value must be a numeric type or None, got {type(value)}")

    module = get_array_module(value)
    nan: bool = bool(module.isnan(value))
    return nan


@overload
def cast_to_float(value: Integer) -> Float: ...


@overload
def cast_to_float(value: Float) -> Float: ...


@overload
def cast_to_float(value: Array) -> Array: ...


def cast_to_float(value: ArrayOrNumeric) -> ArrayOrNumeric:
    """
    Cast integer values to appropriate float types, preserve float types.

    Integer types are promoted to float to avoid losing precision during
    interpolation operations. int64 is promoted to float64, other integer
    types to float32. Float types are preserved as-is.

    Args:
        value: The array or scalar to potentially cast.

    Returns:
        Value casted to float64 for int64 types, float32 for other integer types,
        unchanged for float types.

    Examples:
        >>> cast_to_float(np.array([1, 2, 3], dtype=np.int64))
        array([1., 2., 3.])
        >>> cast_to_float(np.array([1, 2, 3], dtype=np.int32))
        array([1., 2., 3.], dtype=float32)
        >>> cast_to_float(np.array([1.0, 2.0], dtype=np.float32))
        array([1., 2.], dtype=float32)
    """
    if not isinstance(value, ArrayOrScalarClasses):
        raise TypeError(f"Expected value to be an Array, got {type(value)}")

    if isinstance(value, (float, np.floating, xp.floating)):
        return value

    if isinstance(value, (bool, int)):
        return float(value)

    module = get_array_module(value)
    if module.issubdtype(value.dtype, module.integer):
        target_dtype = module.float64 if value.dtype.itemsize >= 8 else module.float32
        return value.astype(target_dtype)

    return value


def infer_dtype(value: Optional[Numeric], dtype: DTypeLike) -> DTypeLike:
    """
    Infers the appropriate dtype for a numeric value based on the provided dtype.

    If the value is NaN or `inf`, and the provided dtype is an integer type,
    the function returns float32 to accommodate NaN values, unless the provided
    dtype is already a floating point type.

    Args:
        value: The numeric value, or `None`.
        dtype: The target dtype to infer from.

    Returns:
        Preserved dtype if value is finite or dtype is floating point,
        otherwise float32.

    Raises:
        TypeError: If the value is not a numeric type or `None`.
    """
    module = get_array_module(value)
    float32: DTypeLike = module.float32
    if value is None:
        return float32

    if not isinstance(value, NumericClasses):
        raise TypeError(f"Value must be a numeric type, got {type(value)}")

    if module.issubdtype(dtype, module.floating) or module.isfinite(value):
        return dtype

    return float32


def pad(array: Array, left: int, right: int, value: Any = 0.0) -> Array:
    """
    Extracts a slice from a 1-dimensional real-valued array
    with optional padding on either side.

    Creates an output array of length (right - left), extracting audio data
    from the specified range. If the range extends beyond the array bounds,
    the output is padded with the specified value.

    If value is NaN or `inf`, the output array will be of float32 dtype to accommodate NaN values,
    unless the input array is already of a float dtype.

    Args:
        audio: The input audio array.
        left: The starting index (can be negative for left padding).
        right: The ending index (can exceed array length for right padding).
        value: The value to use for padding. Defaults to 0.0.

    Returns:
        An array of length (right - left) containing the extracted and padded data.

    Raises:
        TypeError: If array is not a numpy array, or if left/right are not integers.
        ValueError: If left is greater than right, or the array is not 1-dimensional.

    Examples:
        >>> audio = np.array([1, 2, 3, 4, 5])
        >>> pad(audio, -2, 7, value=0)
        array([0, 0, 1, 2, 3, 4, 5, 0, 0])
        >>> pad(audio, 1, 4, value=0)
        array([2, 3, 4])
    """
    if not isinstance(array, ArrayClasses):
        raise TypeError(f"Expected array to be Array, got {type(array)}")

    if array.ndim != 1:
        raise ValueError("Array must be 1-dimensional")

    if not isinstance(left, int) or not isinstance(right, int):
        raise TypeError("Left and right padding values must be integers")

    if left > right:
        raise ValueError("Left padding cannot be greater than right padding")

    module = get_array_module(array)
    n = len(array)
    length = right - left
    dtype = infer_dtype(value, array.dtype)
    output = module.full(length, value, dtype=dtype)

    valid_left = max(left, 0)
    valid_right = min(right, n)

    insert_left = valid_left - left
    insert_right = insert_left + (valid_right - valid_left)

    if valid_right > valid_left:
        output[insert_left:insert_right] = array[valid_left:valid_right]

    return output


def trim(array: Array) -> Array:
    """
    Removes consecutive duplicate values from the end of an array.

    Finds the last position where the array value changes and returns
    the array up to and including one instance of the final value.

    Args:
        array: The input array to trim.

    Returns:
        The trimmed array with trailing duplicates removed, keeping one
        instance of each unique value.

    Raises:
        TypeError: If array is not a numpy array.
        ValueError: If array is not 1-dimensional.

    Examples:
        >>> trim(np.array([1, 1, 2, 2, 3, 3, 3, 3]))
        array([1, 1, 2, 2, 3])
        >>> trim(np.array([5, 5, 5, 5]))
        array([5])
    """
    if not isinstance(array, ArrayClasses):
        raise TypeError(f"Expected array to be Array, got {type(array)}")

    if array.ndim != 1:
        raise ValueError("Array must be 1-dimensional")

    module = get_array_module(array)
    diff = module.diff(array)
    ends = module.where(diff != 0)[0]

    if len(ends) == 0:
        return array[:1]

    last_end = ends[-1]
    last_value = array[last_end + 1]

    return module.concatenate([array[: last_end + 1], [last_value]])


def is_increasing(array: Array) -> bool:
    """
    Check if array values are strictly increasing.

    Args:
        array: Array to check.

    Returns:
        True if each element is strictly greater than the previous one,
        False otherwise.

    Examples:
        >>> is_increasing(np.array([1, 2, 5, 10]))
        True
        >>> is_increasing(np.array([1, 2, 2, 5]))
        False
    """
    module = get_array_module(array)
    return bool(module.all(module.diff(array) > 0))
