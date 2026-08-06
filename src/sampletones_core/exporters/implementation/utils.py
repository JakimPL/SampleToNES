from typing import List

import numpy as np


def center_pitch(
    initial_pitch: int,
    pitches: List[int],
) -> int:
    """
    Picks the pitch at the midpoint of a contour's range.

    Measuring a contour's offsets from the midpoint of its ``(min, max)`` range keeps an
    arpeggio's relative steps small and straddling zero around one center pitch. An empty
    contour keeps the reference where it is.

    Args:
        initial_pitch: Reference pitch the offsets are measured against.
        pitches: Absolute pitches the contour covers.

    Returns:
        The center pitch: ``initial_pitch`` plus the midpoint of the offsets' range.
    """
    if not pitches:
        return initial_pitch

    differences = [pitch - initial_pitch for pitch in pitches]
    array = np.array(differences, dtype=np.int8)
    max_value = np.max(array)
    min_value = np.min(array)
    mean_value = (max_value + min_value) // 2
    return int(initial_pitch + mean_value)
