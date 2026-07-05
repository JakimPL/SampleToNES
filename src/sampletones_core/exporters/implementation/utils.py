from typing import List, Tuple

import numpy as np


def center_pitches(initial_pitch: int, pitches: List[int]) -> Tuple[int, np.ndarray]:
    """
    Args:
        initial_pitch: The pitch to be placed at the beginning of the collection.
        pitches: The list of pitches to be rearranged.
    """
    differences = [pitch - initial_pitch for pitch in pitches]
    array = np.array(differences, dtype=np.int8)
    max_value = np.max(array)
    min_value = np.min(array)
    mean_value = (max_value + min_value) // 2
    return int(initial_pitch + mean_value), array - mean_value
