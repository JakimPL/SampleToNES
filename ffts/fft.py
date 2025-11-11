from functools import lru_cache
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field
from scipy.fft import rfft, rfftfreq

from constants.general import MAX_TRANSFORMATION_GAMMA
from ffts.transformations import LinearExponentialMorpher, Transformations
from typehints.general import (
    BinaryTransformation,
    MultaryTransformation,
    UnaryTransformation,
)


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
    return density_weights * perceptual_weights


class FFTTransformer(BaseModel):
    transformations: Transformations = Field(..., description="FFT feature transformations")
    base_operation: UnaryTransformation = Field(
        default=np.abs,
        description="Base operation for FFT calculations. Default is the absolute value, change with caution",
    )

    @classmethod
    def from_gamma(cls, gamma: int) -> "FFTTransformer":
        assert 0 <= gamma <= MAX_TRANSFORMATION_GAMMA, f"Gamma must be in [0, {MAX_TRANSFORMATION_GAMMA}]"
        morpher = LinearExponentialMorpher(gamma / MAX_TRANSFORMATION_GAMMA)
        transformations = morpher.transformations
        return cls(transformations=transformations)

    def compose(self, callable: MultaryTransformation) -> MultaryTransformation:
        def composition(*args: np.ndarray) -> np.ndarray:
            return self.base_operation(callable(*args))

        return composition

    def base(self, fft: np.ndarray) -> np.ndarray:
        return self.base_operation(fft)

    def operation(self, fft: np.ndarray) -> np.ndarray:
        return self.transformations.operation(fft)

    def inverse(self, fft: np.ndarray) -> np.ndarray:
        return self.transformations.inverse(fft)

    def binary(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
        callable: BinaryTransformation,
    ) -> np.ndarray:
        binary_operation = self.compose(callable)
        return self.transformations.binary(fft1, fft2, binary_operation)

    def calculate(
        self,
        audio: np.ndarray,
        fft_size: Optional[int] = None,
    ) -> np.ndarray:
        fft = self.base_operation(calculate_fft(audio, fft_size))
        return self.transformations.inverse(fft)

    def add(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
    ) -> np.ndarray:
        return self.binary(fft1, fft2, np.add)

    def subtract(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
    ) -> np.ndarray:
        return self.binary(fft1, fft2, np.subtract)

    def multiply(
        self,
        fft: np.ndarray,
        scalar: float,
    ) -> np.ndarray:
        return self.transformations.multiply(fft, scalar, self.base_operation)
