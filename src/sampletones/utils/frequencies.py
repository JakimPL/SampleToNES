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
    """
    Converts a MIDI-style pitch value to its corresponding frequency in Hz.

    Uses the equal temperament tuning system where each semitone is separated
    by a factor of 2^(1/12).

    Args:
        pitch: The MIDI pitch number (0-127, where 69 is typically A4).
        a4_frequency: The reference frequency for A4 in Hz. Defaults to 440.0 Hz.
        a4_pitch: The MIDI pitch number for A4. Defaults to 69.

    Returns:
        The frequency in Hz corresponding to the given pitch.

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
    return a4_frequency * (2 ** ((pitch - a4_pitch) / 12))


def frequency_to_pitch(frequency: float, a4_frequency: float = A4_FREQUENCY, a4_pitch: int = A4_PITCH) -> int:
    """
    Converts a frequency in Hz to the nearest MIDI-style pitch value.

    Uses logarithmic conversion based on the equal temperament tuning system.
    Returns 0 for frequencies at or below 0 Hz.

    Args:
        frequency: The frequency in Hz to convert.
        a4_frequency: The reference frequency for A4 in Hz. Defaults to 440.0 Hz.
        a4_pitch: The MIDI pitch number for A4. Defaults to 69.

    Returns:
        The nearest integer MIDI pitch number, or 0 if frequency <= 0.

    Examples:
        >>> frequency_to_pitch(440.0)  # A4
        69
        >>> frequency_to_pitch(880.0)  # A5
        81
        >>> frequency_to_pitch(261.63)  # ~Middle C
        60
        >>> frequency_to_pitch(0.0)  # Invalid frequency
        0
        >>> frequency_to_pitch(-100.0)  # Invalid frequency
        0
    """
    if frequency <= 0:
        return 0

    pitch: int = round(a4_pitch + 12 * (np.log2(frequency / a4_frequency)))
    return pitch


def pitch_to_name(pitch: int, transpose: int = 0) -> str:
    """
    Converts a MIDI pitch value to a human-readable note name
    consistent with FamiTracker.

    Args:
        pitch: The MIDI pitch number to convert.
        transpose: Optional semitone transposition to apply. Defaults to 0.

    Returns:
        A string representing the note name and octave (e.g., "C4", "A#3").

    Examples:
        >>> pitch_to_name(60)  # Middle C
        'C4'
        >>> pitch_to_name(69)  # A4
        'A4'
        >>> pitch_to_name(61)  # C# above middle C
        'C#4'
        >>> pitch_to_name(60, transpose=2)  # Middle C transposed up 2 semitones
        'D4'
        >>> pitch_to_name(60, transpose=-12)  # Middle C transposed down an octave
        'C3'
    """
    pitch += transpose
    octave = (pitch // 12) - 2
    note_index = pitch % 12
    return f"{NOTE_NAMES[note_index]}{octave}"


def period_to_name(period: int) -> str:
    """
    Converts a noise period index to its hexadecimal name representation,
    used in FamiTracker.

    Args:
        period: The period index (0-15 for NES noise channel).

    Returns:
        A string in hexadecimal format followed by "-#" (e.g., "0-#", "F-#").

    Examples:
        >>> period_to_name(0)
        '0-#'
        >>> period_to_name(10)
        'A-#'
        >>> period_to_name(15)
        'F-#'
    """
    return f"{period:X}-#"


def clamp_pitch(pitch: int, min_pitch: int = MIN_PITCH, max_pitch: int = MAX_PITCH) -> int:
    """
    Restricts a pitch value to be within the valid range.

    Args:
        pitch: The pitch value to clamp.
        min_pitch: The minimum allowed pitch. Defaults to MIN_PITCH.
        max_pitch: The maximum allowed pitch. Defaults to MAX_PITCH.

    Returns:
        The pitch value clamped to the range [min_pitch, max_pitch].

    Examples:
        >>> clamp_pitch(60)  # Within range
        60
        >>> clamp_pitch(0)  # Below minimum, 33 is the default minimum
        33
        >>> clamp_pitch(150)  # Above maximum, 119 is the default maximum
        119
    """
    return int(clamp(pitch, min_pitch, max_pitch))


def clamp_period(period: int, min_period: int = 0, max_period: int = MAX_PERIOD) -> int:
    """
    Restricts a period value to be within the valid range.

    Args:
        period: The period value to clamp.
        min_period: The minimum allowed period. Defaults to 0.
        max_period: The maximum allowed period. Defaults to MAX_PERIOD.

    Returns:
        The period value clamped to the range [min_period, max_period].

    Examples:
        >>> clamp_period(5)  # Within range
        5
        >>> clamp_period(-10)  # Below minimum
        0
        >>> clamp_period(100)  # Above maximum, where max_period is 15
        15
    """
    return int(clamp(period, min_period, max_period))


def sanitize(name: str) -> str:
    """
    Sanitizes a string by removing leading/trailing whitespace
    and converting to uppercase.

    Args:
        name: The string to sanitize.

    Returns:
        The sanitized string in uppercase with stripped whitespace.

    Examples:
        >>> sanitize("  hello world  ")
        'HELLO WORLD'
        >>> sanitize("c#4")
        'C#4'
        >>> sanitize("  A4  ")
        'A4'
    """
    return name.strip().upper()


def sanitize_pitch(name: str) -> str:
    """
    Sanitizes a pitch name by keeping only valid pitch-related characters.

    Removes whitespace, converts to uppercase, and filters to only allow:
    digits (0-9), hyphen (-), sharp (#), and hexadecimal letters (A-F).

    Args:
        name: The pitch name string to sanitize.

    Returns:
        The sanitized pitch name containing only valid characters.

    Examples:
        >>> sanitize_pitch("C#4")
        'C#4'
        >>> sanitize_pitch("  a#3  ")
        'A#3'
        >>> sanitize_pitch("C@4!")
        'C4'
        >>> sanitize_pitch("F-#")  # invalid as a pitch name though
        'F-#'
    """
    return "".join([character for character in sanitize(name) if character in "0123456789-#ABCDEF"])


def sanitize_period(name: str) -> str:
    """
    Sanitizes a period name by keeping only valid hexadecimal characters.
    Ignores any non-hexadecimal characters as they can be inferred.

    Removes whitespace, converts to uppercase, and filters to only allow
    hexadecimal digits (0-9, A-F).

    Args:
        name: The period name string to sanitize.

    Returns:
        The sanitized period name containing only hexadecimal characters.

    Examples:
        >>> sanitize_period("0A")
        '0A'
        >>> sanitize_period("  f  ")
        'F'
        >>> sanitize_period("A-#")
        'A'
        >>> sanitize_period("10@!")
        '10'
    """
    return "".join([character for character in sanitize(name) if character in "0123456789ABCDEF"])


MIN_AVAILABLE_FREQUENCY = pitch_to_frequency(MIN_PITCH)
MAX_AVAILABLE_FREQUENCY = pitch_to_frequency(MAX_PITCH)
NAME_TO_PITCH = {pitch_to_name(pitch): pitch for pitch in range(MIN_PITCH, MAX_PITCH + 1)}
NAME_TO_PERIOD = {period_to_name(period): period for period in range(len(NOISE_PERIODS))}
SANITIZED_NAME_TO_PITCH = {sanitize_pitch(pitch_to_name(pitch)): pitch for pitch in range(MIN_PITCH, MAX_PITCH + 1)}
SANITIZED_NAME_TO_PERIOD = {sanitize_period(period_to_name(period)): period for period in range(len(NOISE_PERIODS))}
