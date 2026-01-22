from functools import lru_cache
from typing import Optional, cast

import numpy as np
from scipy.fft import rfft, rfftfreq


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    fft_size = audio.shape[0] if fft_size is None else fft_size
    array = cast(np.ndarray, rfft(audio, fft_size))
    return array[1:]


def calculate_frequencies(fragment_length: int, sample_rate: int) -> np.ndarray:
    return rfftfreq(fragment_length, 1.0 / sample_rate)


def a_weighting(frequencies: np.ndarray) -> np.ndarray:
    frequencies = np.maximum(frequencies, 1e-6)
    squares = frequencies**2
    numerator = 12194**2 * squares**2
    denominator = (squares + 20.6**2) * np.sqrt((squares + 107.7**2) * (squares + 737.9**2)) * (squares + 12194**2)

    a_weight: np.ndarray = numerator / denominator
    normalized_a_weight: np.ndarray = a_weight / np.max(a_weight)
    return normalized_a_weight


@lru_cache(maxsize=128)
def calculate_weights(fragment_length: int, sample_rate: int) -> np.ndarray:
    frequencies = calculate_frequencies(fragment_length, sample_rate)[1:]
    density_weights = 1.0 / frequencies
    perceptual_weights = a_weighting(frequencies)

    weights: np.ndarray = density_weights * perceptual_weights
    normalized_weights: np.ndarray = weights / np.sum(weights)
    return normalized_weights
