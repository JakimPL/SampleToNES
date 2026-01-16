from typing import Any, Dict, Optional, Union, overload

import numpy as np

from sampletones.typehints import Numeric


def next_power_of_two(length: int) -> int:
    """
    Calculates the next power of two greater than or equal to the given length.

    Args:
        length: The input value.

    Returns:
        The smallest power of two that is greater than or equal to length.

    Raises:
        ValueError: If length is negative.
        OverflowError: If length is too large to compute the next power of two.

    Examples:
        >>> next_power_of_two(0)
        1
        >>> next_power_of_two(5)
        8
        >>> next_power_of_two(8)
        8
        >>> next_power_of_two(17)
        32
    """
    if length < 0:
        raise ValueError("Length must be a positive integer")

    if length == 0:
        return 1

    if length > (1 << 63):
        raise OverflowError("Length is too large to compute the next power of two")

    return 1 << (length - 1).bit_length()


@overload
def clamp(
    value: Union[int, np.integer],
    min_value: Optional[Union[int, np.integer]] = None,
    max_value: Optional[Union[int, np.integer]] = None,
) -> int: ...


@overload
def clamp(
    value: Union[float, np.floating],
    min_value: Optional[Union[float, np.floating]] = None,
    max_value: Optional[Union[float, np.floating]] = None,
) -> float: ...


def clamp(
    value: Numeric,
    min_value: Optional[Numeric] = None,
    max_value: Optional[Numeric] = None,
) -> Union[int, float]:
    """
    Restricts a value to be within a specified range.
    Maximum takes precedence over minimum if
    `max_value` is less than `min_value`.

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
        0.0
    """
    if not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"Value must be a numeric type, got {type(value)}")

    if min_value is not None and not isinstance(min_value, (int, float, np.integer, np.floating)):
        raise TypeError(f"Unsupported type for min_value: {type(min_value)}")

    if max_value is not None and not isinstance(max_value, (int, float, np.integer, np.floating)):
        raise TypeError(f"Unsupported type for max_value: {type(max_value)}")

    all_integers = all(isinstance(v, (int, np.integer)) for v in (value, min_value, max_value) if v is not None)

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


def pad(array: np.ndarray, left: int, right: int, value: Any = 0.0) -> np.ndarray:
    """
    Extracts a slice from a 1-dimensional real-valued array
    with optional padding on either side.

    Creates an output array of length (right - left), extracting audio data
    from the specified range. If the range extends beyond the array bounds,
    the output is padded with the specified value.

    If value is NaN, the output array will be of float32 dtype to accommodate NaN values,
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
    if not isinstance(array, np.ndarray):
        raise TypeError(f"Expected array to be np.ndarray, got {type(array)}")

    if array.ndim != 1:
        raise ValueError("Array must be 1-dimensional")

    if not isinstance(left, int) or not isinstance(right, int):
        raise TypeError("Left and right padding values must be integers")

    if left > right:
        raise ValueError("Left padding cannot be greater than right padding")

    n = len(array)
    length = right - left
    value = np.nan if value is None or (isinstance(value, (float, np.floating)) and np.isnan(value)) else value
    dtype = array.dtype if np.issubdtype(array.dtype, np.floating) or value is not np.nan else np.float32
    output = np.full(length, value, dtype=dtype)

    valid_left = max(left, 0)
    valid_right = min(right, n)

    insert_left = valid_left - left
    insert_right = insert_left + (valid_right - valid_left)

    if valid_right > valid_left:
        output[insert_left:insert_right] = array[valid_left:valid_right]

    return output


def trim(array: np.ndarray) -> np.ndarray:
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
    if not isinstance(array, np.ndarray):
        raise TypeError(f"Expected array to be np.ndarray, got {type(array)}")

    if array.ndim != 1:
        raise ValueError("Array must be 1-dimensional")

    diff = np.diff(array)
    ends = np.where(diff != 0)[0]

    if len(ends) == 0:
        return array[:1]

    last_end = ends[-1]
    last_value = array[last_end + 1]

    return np.concatenate([array[: last_end + 1], [last_value]])


def first_key_for_value(dictionary: Dict[Any, Any], target: Any) -> Any:
    """
    Finds the first key in a dictionary that maps to the specified value.

    Respects the insertion order of keys in the dictionary.

    Args:
        dictionary: The dictionary to search.
        target: The value to search for.

    Returns:
        The first key that maps to the target value, or None if not found.

    Examples:
        >>> first_key_for_value({'a': 1, 'b': 2, 'c': 1}, 2)
        'b'
        >>> first_key_for_value({'c': 1, 'b': 2, 'a': 1}, 1)
        'c'
        >>> first_key_for_value({'a': 1, 'b': 2}, 3)
        None
    """
    if not isinstance(dictionary, dict):
        raise TypeError(f"Expected dictionary to be dict, got {type(dictionary)}")

    for key, value in dictionary.items():
        if value == target:
            return key

    return None
