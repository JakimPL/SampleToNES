from typing import Any, Dict, Union, overload

import numpy as np

from sampletones.typehints import Numeric


def next_power_of_two(length: int) -> int:
    return 1 << (length - 1).bit_length()


@overload
def clamp(
    value: Union[int, np.integer],
    min_value: Union[int, np.integer],
    max_value: Union[int, np.integer],
) -> int: ...


@overload
def clamp(
    value: Union[float, np.floating],
    min_value: Union[float, np.floating],
    max_value: Union[float, np.floating],
) -> float: ...


def clamp(
    value: Numeric,
    min_value: Numeric,
    max_value: Numeric,
) -> Union[int, float]:
    if isinstance(value, (int, np.integer)):
        min_value = int(min_value)
        max_value = int(max_value)
        value = int(value)
    else:
        min_value = float(min_value)
        max_value = float(max_value)
        value = float(value)

    return max(min_value, min(value, max_value))


def pad(audio: np.ndarray, left: int, right: int) -> np.ndarray:
    if not isinstance(audio, np.ndarray):
        raise TypeError(f"Expected audio to be np.ndarray, got {type(audio)}")

    if not isinstance(left, int) or not isinstance(right, int):
        raise TypeError("Left and right padding values must be integers")

    n = len(audio)
    length = right - left
    output = np.zeros(length, dtype=audio.dtype)

    valid_left = max(left, 0)
    valid_right = min(right, n)

    insert_left = valid_left - left
    insert_right = insert_left + (valid_right - valid_left)

    if valid_right > valid_left:
        output[insert_left:insert_right] = audio[valid_left:valid_right]

    return output


def trim(array: np.ndarray) -> np.ndarray:
    diff = np.diff(array)
    ends = np.where(diff != 0)[0]

    if len(ends) == 0:
        return array[:1]

    last_end = ends[-1]
    last_value = array[last_end + 1]

    return np.concatenate([array[: last_end + 1], [last_value]])


def first_key_for_value(dictionary: Dict[Any, Any], target: Any) -> Any:
    for key, value in dictionary.items():
        if value == target:
            return key

    return None
