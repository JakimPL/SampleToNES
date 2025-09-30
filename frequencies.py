from typing import Dict

import numpy as np

from constants import A4_FREQUENCY, A4_PITCH, MAX_PITCH, MIN_PITCH
from timer import Timer


def pitch_to_frequency(pitch: int, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> float:
    return a4_frequency * (2 ** ((pitch - a4_pitch) / 12))


def frequency_to_pitch(frequency: float, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> int:
    if frequency <= 0:
        return 0
    return round(a4_pitch + 12 * (np.log2(frequency / a4_frequency)))


def get_frequency_table(
    a4_frequency: float = A4_FREQUENCY,
    a4_pitch: int = A4_PITCH,
    min_pitch: int = MIN_PITCH,
    max_pitch: int = MAX_PITCH,
) -> Dict[int, float]:
    timer = Timer()
    frequencies = {}
    for note in range(min_pitch, max_pitch + 1):
        frequency = pitch_to_frequency(note, a4_frequency, a4_pitch)
        timer.frequency = frequency
        frequencies[note] = timer.frequency

    return frequencies


MIN_AVAILABLE_FREQUENCY = pitch_to_frequency(MIN_PITCH)
MAX_AVAILABLE_FREQUENCY = pitch_to_frequency(MAX_PITCH)
