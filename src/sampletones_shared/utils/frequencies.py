import numpy as np

from sampletones_shared.constants.music import (
    A4_FREQUENCY,
    A4_PITCH,
    LIMIT_MAX_PITCH,
    LIMIT_MIN_PITCH,
    OCTAVE_SEMITONES,
)


def validate_pitch(pitch: int) -> None:
    """
    Validates that a pitch value is an integer within the range 24-127.

    Args:
        pitch: The pitch value to validate.

    Raises:
        TypeError: If pitch is not an integer.
        ValueError: If pitch is outside the range 24-127.
    """
    if not isinstance(pitch, int):
        raise TypeError("Pitch must be an integer value")

    if not LIMIT_MIN_PITCH <= pitch <= LIMIT_MAX_PITCH:
        raise ValueError(f"Pitch must be in the range {LIMIT_MIN_PITCH}-{LIMIT_MAX_PITCH}")


def validate_frequency(frequency: float) -> None:
    """
    Validates that a frequency value is a positive finite number.

    Args:
        frequency: The frequency value to validate.

    Raises:
        TypeError: If frequency is not a numeric type.
        ValueError: If frequency is not a positive finite number.
    """
    if not isinstance(frequency, (int, float)):
        raise TypeError("Frequency must be a numeric value")

    if np.isinf(frequency) or np.isnan(frequency):
        raise ValueError("Frequency must be a positive finite number")

    if frequency <= 0:
        raise ValueError("Frequency must be a positive value")


def pitch_to_frequency(
    pitch: int,
    a4_frequency: float = A4_FREQUENCY,
    a4_pitch: int = A4_PITCH,
) -> float:
    """
    Converts a MIDI-style pitch value to its corresponding frequency in Hz.

    Uses the equal temperament tuning system where each semitone is separated
    by a factor of 2^(1/12).

    Args:
        pitch: The MIDI pitch number (24-127, where 69 is typically A4).
        a4_frequency: The reference frequency for A4 in Hz. Defaults to 440.0 Hz.
        a4_pitch: The MIDI pitch number for A4. Defaults to 69.

    Returns:
        The frequency in Hz corresponding to the given pitch.

    Raises:
        TypeError: If pitch is not an integer.
        TypeError: If a4_frequency is not a numeric type.
        TypeError: If a4_pitch is not an integer.
        ValueError: If pitch is outside the range 24-127.
        ValueError: If a4_pitch is outside the range 24-127.
        ValueError: If a4_frequency is not a positive finite number.
        ValueError: If calculated frequency is not a positive finite number.

    Examples:
        >>> pitch_to_frequency(69)  # A4
        440.0
        >>> pitch_to_frequency(57)  # A3 (one octave below A4)
        220.0
        >>> pitch_to_frequency(60)  # Middle C (C4)
        261.6255653005986
        >>> pitch_to_frequency(69, a4_frequency=432.0)  # A4 with different tuning
        432.0
    """
    validate_pitch(pitch)
    validate_pitch(a4_pitch)
    validate_frequency(a4_frequency)

    frequency: float = a4_frequency * (2 ** ((pitch - a4_pitch) / OCTAVE_SEMITONES))
    validate_frequency(frequency)
    return frequency


def frequency_to_pitch(
    frequency: float,
    a4_frequency: float = A4_FREQUENCY,
    a4_pitch: int = A4_PITCH,
) -> int:
    """
    Converts a frequency in Hz to the nearest MIDI-style pitch value.

    Uses logarithmic conversion based on the equal temperament tuning system.
    Returns 0 for frequencies at or below 0 Hz.

    Args:
        frequency: The frequency in Hz to convert.
        a4_frequency: The reference frequency for A4 in Hz. Defaults to 440.0 Hz.
        a4_pitch: The MIDI pitch number for A4. Defaults to 69.

    Returns:
        The nearest integer MIDI pitch number.

    Raises:
        TypeError: If frequency is not a numeric type.
        TypeError: If a4_frequency is not a numeric type.
        TypeError: If a4_pitch is not an integer.
        ValueError: If frequency is not a positive finite number.
        ValueError: If a4_frequency is not a positive finite number.
        ValueError: If calculated pitch is outside the range 24-127.

    Examples:
        >>> frequency_to_pitch(440.0)  # A4
        69
        >>> frequency_to_pitch(880.0)  # A5
        81
        >>> frequency_to_pitch(261.63)  # ~middle C
        60
        >>> frequency_to_pitch(0.0)  # invalid frequency
        Traceback (most recent call last):
            ...
        ValueError: Frequency must be a positive value
    """
    validate_frequency(frequency)
    validate_frequency(a4_frequency)
    validate_pitch(a4_pitch)

    pitch: int = round(a4_pitch + OCTAVE_SEMITONES * (np.log2(frequency / a4_frequency)))
    validate_pitch(pitch)
    return pitch
