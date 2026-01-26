from functools import lru_cache
from typing import Optional, cast

import numpy as np
from scipy.fft import rfft, rfftfreq


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    """
    Compute the real-valued Fast Fourier Transform of an audio signal.

    Calculates the FFT and removes the DC component (first element).
    Uses scipy.fft.rfft which is optimized for real-valued input signals.

    Args:
        audio: Input audio signal array.
        fft_size: Size of the FFT. If None, uses the length of the audio array.

    Returns:
        Complex FFT coefficients with DC component removed, shape (fft_size//2,).

    Examples:
        >>> audio = np.random.randn(1024)
        >>> fft_result = calculate_fft(audio)
        >>> fft_result.shape
        (512,)
    """
    fft_size = audio.shape[0] if fft_size is None else fft_size
    array = cast(np.ndarray, rfft(audio, fft_size))
    return array[1:]


def calculate_fft_frequencies(fragment_length: int, sample_rate: int) -> np.ndarray:
    """
    Calculate frequency bins for a real-valued FFT.

    Computes the frequencies corresponding to each FFT bin for a real signal.
    Uses scipy.fft.rfftfreq which returns positive frequencies only.

    Returns frequency edges from 0 Hz up to Nyquist frequency.

    Args:
        fragment_length: Length of the audio fragment (FFT size).
        sample_rate: Sampling rate in Hz.

    Returns:
        Array of frequency values in Hz, shape (fragment_length//2 + 1,).

    Examples:
        >>> freqs = calculate_fft_frequencies(1024, 44100)
        >>> freqs.shape
        (513,)
        >>> float(freqs[0])
        0.0
        >>> float(freqs[-1])
        22050.0
    """
    return rfftfreq(fragment_length, 1.0 / sample_rate)


def a_weighting(frequencies: np.ndarray) -> np.ndarray:
    """
    Apply A-weighting perceptual filter to frequency values.

    A-weighting approximates the frequency response of human hearing,
    emphasizing mid-range frequencies while attenuating very low and very high frequencies.
    Implements the standard A-weighting curve defined in IEC 61672-1.

    The weights are normalized such that the maximum weight is 1.0.
    Frequencies below 1e-6 Hz are clamped to prevent division by zero.

    Args:
        frequencies: Array of frequency values in Hz.

    Returns:
        Normalized A-weighting values, shape matching input.
        Values are in [0, 1] with maximum at ~1kHz-4kHz range.

    Examples:
        >>> freqs = np.array([100.0, 1000.0, 10000.0])
        >>> weights = a_weighting(freqs)
        >>> weights.shape
        (3,)
    """
    frequencies = np.maximum(frequencies, 1e-6)
    squares = frequencies**2
    numerator = 12194**2 * squares**2
    denominator = (squares + 20.6**2) * np.sqrt((squares + 107.7**2) * (squares + 737.9**2)) * (squares + 12194**2)

    a_weight: np.ndarray = numerator / denominator
    normalized_a_weight: np.ndarray = a_weight / np.max(a_weight)
    return normalized_a_weight


@lru_cache(maxsize=128)
def calculate_weights(fragment_length: int, sample_rate: int) -> np.ndarray:
    """
    Calculate combined frequency weights for spectrum analysis.

    Computes weights that combine frequency density compensation with
    A-weighting perceptual filtering. The density weights (1/f) compensate
    for the logarithmic spacing of frequencies, while A-weighting emphasizes
    perceptually important frequencies.

    The result is normalized to sum to 1.0.

    Args:
        fragment_length: Length of the audio fragment (FFT size).
        sample_rate: Sampling rate in Hz.

    Returns:
        Normalized combined weights, shape (fragment_length//2,).
        Sum of weights equals 1.0.

    Examples:
        >>> weights = calculate_weights(1024, 44100)
        >>> weights.shape
        (512,)
        >>> bool(np.isclose(weights.sum(), 1.0))
        True
    """
    frequencies = calculate_fft_frequencies(fragment_length, sample_rate)[1:]
    density_weights = 1.0 / frequencies
    perceptual_weights = a_weighting(frequencies)

    weights: np.ndarray = density_weights * perceptual_weights
    normalized_weights: np.ndarray = weights / np.sum(weights)
    return normalized_weights
