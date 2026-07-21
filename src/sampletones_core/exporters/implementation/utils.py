from typing import List, Tuple

import numpy as np


def center_pitches(
    initial_pitch: int,
    pitches: List[int],
) -> Tuple[int, np.ndarray]:
    """
    Re-centers a pitch sequence around the midpoint of its range.

    Shifts every pitch by the midpoint of its ``(min, max)`` range so the offsets
    straddle zero, keeping an arpeggio's relative steps small around one center pitch.

    Args:
        initial_pitch: Reference pitch the offsets are measured against.
        pitches: Absolute pitches to re-center.

    Returns:
        The center pitch (``initial_pitch`` plus the range midpoint) and the array of
        signed offsets from that center, so each original pitch equals center + offset.
    """
    differences = [pitch - initial_pitch for pitch in pitches]
    array = np.array(differences, dtype=np.int8)
    max_value = np.max(array)
    min_value = np.min(array)
    mean_value = (max_value + min_value) // 2
    return int(initial_pitch + mean_value), array - mean_value
