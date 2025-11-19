from functools import lru_cache
from typing import Optional

import numpy as np
from scipy.fft import rfft, rfftfreq


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    fft_size = audio.shape[0] if fft_size is None else fft_size
    return rfft(audio, fft_size)[1:]


def calculate_frequencies(fragment_length: int, sample_rate: int) -> np.ndarray:
    return rfftfreq(fragment_length, 1 / sample_rate)[1:]


def a_weighting(frequencies: np.ndarray) -> np.ndarray:
    frequencies = np.maximum(frequencies, 1e-6)
    squares = frequencies**2
    numerator = 12194**2 * squares**2
    denominator = (squares + 20.6**2) * np.sqrt((squares + 107.7**2) * (squares + 737.9**2)) * (squares + 12194**2)

    a_weight = numerator / denominator
    return a_weight / np.max(a_weight)


@lru_cache(maxsize=128)
def calculate_weights(fragment_length: int, sample_rate: int) -> np.ndarray:
    frequencies = calculate_frequencies(fragment_length, sample_rate)
    density_weights = 1.0 / frequencies
    perceptual_weights = a_weighting(frequencies)
    weights = density_weights * perceptual_weights
    return weights / np.sum(weights)
