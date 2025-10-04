import json
from typing import Any, Dict

import numpy as np


def next_power_of_two(length: int) -> int:
    return 1 << (length - 1).bit_length()


def pad(audio: np.ndarray, left: int, right: int) -> np.ndarray:
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


def dump(dictionary: Dict[str, Any]) -> str:
    return json.dumps(dictionary, separators=(",", ":"))


def first_key_for_value(dictionary: dict, target: Any) -> Any:
    for key, value in dictionary.items():
        if value == target:
            return key

    return None
