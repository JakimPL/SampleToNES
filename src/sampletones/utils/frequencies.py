import numpy as np

from sampletones.constants.general import (
    A4_FREQUENCY,
    A4_PITCH,
    MAX_PITCH,
    MIN_PITCH,
    NOTE_NAMES,
)


def pitch_to_frequency(pitch: int, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> float:
    return a4_frequency * (2 ** ((pitch - a4_pitch) / 12))


def frequency_to_pitch(frequency: float, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> int:
    if frequency <= 0:
        return 0
    return round(a4_pitch + 12 * (np.log2(frequency / a4_frequency)))


def pitch_to_name(pitch: int, transpose: int = 0) -> str:
    pitch += transpose
    octave = (pitch // 12) - 2
    note_index = pitch % 12
    return f"{NOTE_NAMES[note_index]}{octave}"


MIN_AVAILABLE_FREQUENCY = pitch_to_frequency(MIN_PITCH)
MAX_AVAILABLE_FREQUENCY = pitch_to_frequency(MAX_PITCH)
