import os
from pathlib import Path
from typing import Any

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


def first_key_for_value(dictionary: dict, target: Any) -> Any:
    for key, value in dictionary.items():
        if value == target:
            return key

    return None


def shorten_path(path: Path) -> str:
    path = path.expanduser().resolve()
    parts = path.parts
    root = parts[0]

    if len(parts) <= 3:
        return str(path)

    first_dir = parts[1]
    last_dir = parts[-2]
    filename = parts[-1]

    if len(parts) == 4:
        return str(path)
    else:
        return os.sep.join([root.rstrip(os.sep), first_dir, "...", last_dir, filename])
