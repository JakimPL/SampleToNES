from typing import Dict

from constants import A4_FREQUENCY, A4_PITCH, MAX_PITCH, MIN_PITCH
from timer import Timer


def get_frequency_table(
        a4_frequency: float = A4_FREQUENCY,
        a4_pitch: int = A4_PITCH,
        min_pitch: int = MIN_PITCH,
        max_pitch: int = MAX_PITCH,
) -> Dict[int, float]:
    timer = Timer()
    frequencies = {}
    for note in range(min_pitch, max_pitch + 1):
        frequency = a4_frequency * (2 ** ((note - a4_pitch) / 12))
        timer.frequency = frequency
        frequencies[note] = timer.frequency

    return frequencies
