from typing import Dict

import numpy as np

from config import Config
from constants import A4_FREQUENCY, A4_PITCH, MAX_PITCH, MIN_PITCH
from timers.phase import PhaseTimer


def pitch_to_frequency(pitch: int, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> float:
    return a4_frequency * (2 ** ((pitch - a4_pitch) / 12))


def frequency_to_pitch(frequency: float, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> int:
    if frequency <= 0:
        return 0
    return round(a4_pitch + 12 * (np.log2(frequency / a4_frequency)))


def get_frequency_table(config: Config) -> Dict[int, float]:
    timer = PhaseTimer(sample_rate=config.sample_rate, change_rate=config.change_rate)
    frequencies = {}
    for note in range(config.min_pitch, config.max_pitch + 1):
        frequency = pitch_to_frequency(note, config.a4_frequency, config.a4_pitch)
        timer.frequency = frequency
        frequencies[note] = timer.frequency

    return frequencies


MIN_AVAILABLE_FREQUENCY = pitch_to_frequency(MIN_PITCH)
MAX_AVAILABLE_FREQUENCY = pitch_to_frequency(MAX_PITCH)
