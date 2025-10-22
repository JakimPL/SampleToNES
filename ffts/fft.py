from functools import lru_cache
from typing import Callable, Optional

import numpy as np
import scipy.fft
from pydantic import BaseModel, Field

from ffts.transformations import TRANSFORMATIONS, Transformations
from typehints.general import TransformationName


def calculate_fft(audio: np.ndarray, fft_size: Optional[int] = None) -> np.ndarray:
    fft_size = audio.shape[0] if fft_size is None else fft_size
    return scipy.fft.rfft(audio, fft_size)[1:]


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


class FFTTransformer(BaseModel):
    transformations: Transformations = Field(..., description="Transformations to be applied")

    @classmethod
    def from_name(cls, name: TransformationName) -> "Transformations":
        return cls(transformations=TRANSFORMATIONS[name])

    def log_arfft_operation(
        self,
        larfft1: np.ndarray,
        larfft2: np.ndarray,
        binary_operation: Callable[[np.ndarray, np.ndarray], np.ndarray],
    ) -> np.ndarray:
        return self.transformations.binary(larfft1, larfft2, binary_operation)

    def calculate_log_arfft(
        self,
        audio: np.ndarray,
        fft_size: Optional[int] = None,
    ) -> np.ndarray:
        afft = np.abs(calculate_fft(audio, fft_size))
        return self.transformations.inverse(afft)

    def log_arfft_subtract(
        self,
        larfft1: np.ndarray,
        larfft2: np.ndarray,
    ) -> np.ndarray:
        return self.transformations.binary(larfft1, larfft2, np.subtract)

    def log_arfft_multiply(
        self,
        larfft: np.ndarray,
        scalar: float,
    ) -> np.ndarray:
        return self.transformations.multiply(larfft, scalar, np.abs)
