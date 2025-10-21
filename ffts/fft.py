from functools import lru_cache
from typing import Callable, Optional

import numpy as np
import scipy.fft

from ffts.transformations import DEFAULT_TRANSFORMATION, Transformations


def log_arfft_operation(
    larfft1: np.ndarray,
    larfft2: np.ndarray,
    binary_operation: Callable[[np.ndarray, np.ndarray], np.ndarray],
    transformations: Transformations = DEFAULT_TRANSFORMATION,
) -> np.ndarray:
    return transformations.binary(larfft1, larfft2, binary_operation)


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    fft_size = audio.shape[0] if fft_size is None else fft_size
    return scipy.fft.rfft(audio, fft_size)[1:]


def calculate_log_arfft(
    audio: np.ndarray,
    fft_size: Optional[int] = None,
    transformations: Transformations = DEFAULT_TRANSFORMATION,
) -> np.ndarray:
    afft = np.abs(calculate_fft(audio, fft_size))
    return transformations.inverse(afft)


def log_arfft_subtract(
    larfft1: np.ndarray, larfft2: np.ndarray, transformations: Transformations = DEFAULT_TRANSFORMATION
) -> np.ndarray:
    return transformations.binary(larfft1, larfft2, np.subtract)


def log_arfft_multiply(
    larfft: np.ndarray, scalar: float, transformations: Transformations = DEFAULT_TRANSFORMATION
) -> np.ndarray:
    return transformations.multiply(larfft, scalar, np.abs)


def a_weighting(frequencies: np.ndarray) -> np.ndarray:
    frequencies = np.maximum(frequencies, 1e-6)
    squares = frequencies**2
    numerator = 12194**2 * squares**2
    denominator = (squares + 20.6**2) * np.sqrt((squares + 107.7**2) * (squares + 737.9**2)) * (squares + 12194**2)

    a_weight = numerator / denominator
    return a_weight / np.max(a_weight)


@lru_cache(maxsize=128)
def calculate_weights(fragment_length: int, sample_rate: int) -> np.ndarray:
    frequencies = scipy.fft.rfftfreq(fragment_length, 1 / sample_rate)[1:]
    density_weights = 1.0 / frequencies
    perceptual_weights = a_weighting(frequencies)
    return density_weights * perceptual_weights
