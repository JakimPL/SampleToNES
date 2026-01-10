import numpy as np

from sampletones.constants.general import (
    A4_FREQUENCY,
    A4_PITCH,
    MAX_PERIOD,
    MAX_PITCH,
    MIN_PITCH,
    NOISE_PERIODS,
    NOTE_NAMES,
)

from .common import clamp


def pitch_to_frequency(pitch: int, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> float:
    return a4_frequency * (2 ** ((pitch - a4_pitch) / 12))


def frequency_to_pitch(frequency: float, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> int:
    if frequency <= 0:
        return 0

    pitch: int = round(a4_pitch + 12 * (np.log2(frequency / a4_frequency)))
    return pitch


def pitch_to_name(pitch: int, transpose: int = 0) -> str:
    pitch += transpose
    octave = (pitch // 12) - 2
    note_index = pitch % 12
    return f"{NOTE_NAMES[note_index]}{octave}"


def period_to_name(period: int) -> str:
    return f"{period:X}-#"


def clamp_pitch(pitch: int, min_pitch: int = MIN_PITCH, max_pitch: int = MAX_PITCH) -> int:
    return int(clamp(pitch, min_pitch, max_pitch))


def clamp_period(period: int, min_period: int = 0, max_period: int = MAX_PERIOD) -> int:
    return int(clamp(period, min_period, max_period))


def sanitize(name: str) -> str:
    return name.strip().upper()


def sanitize_pitch(name: str) -> str:
    return "".join([character for character in sanitize(name) if character in "0123456789-#ABCDEF"])


def sanitize_period(name: str) -> str:
    return "".join([character for character in sanitize(name) if character in "0123456789ABCDEF"])


MIN_AVAILABLE_FREQUENCY = pitch_to_frequency(MIN_PITCH)
MAX_AVAILABLE_FREQUENCY = pitch_to_frequency(MAX_PITCH)
NAME_TO_PITCH = {pitch_to_name(pitch): pitch for pitch in range(MIN_PITCH, MAX_PITCH + 1)}
NAME_TO_PERIOD = {period_to_name(period): period for period in range(len(NOISE_PERIODS))}
SANITIZED_NAME_TO_PITCH = {sanitize_pitch(pitch_to_name(pitch)): pitch for pitch in range(MIN_PITCH, MAX_PITCH + 1)}
SANITIZED_NAME_TO_PERIOD = {sanitize_period(period_to_name(period)): period for period in range(len(NOISE_PERIODS))}
