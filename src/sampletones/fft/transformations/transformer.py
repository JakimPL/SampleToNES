from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import MAX_TRANSFORMATION_GAMMA

from ..fft import calculate_fft
from .functions import energy
from .morpher import PowerMorpher
from .transformation import Transformation
from .typehints import BinaryTransformation, UnaryTransformation


class FFTTransformer(BaseModel):
    """
    A Transformation wrapper specifically for FFT features.

    Calculates FFT features with a base operation (`energy` by default) and applies transformations
    of the form:
        `f(x) = x ^ a`

    where `a` is from [0.25, 4] depending on the gamma parameter. The `a` is mapped
    from gamma in [0, 100] to [0.25, 4] such that:
        - `gamma = 0   -> a = 0.25`  (flat features)
        - `gamma = 50  -> a = 1.0`   (standard energy)
        - `gamma = 100 -> a = 4.0`   (sharp features)

    More precisely, the general form of a transformation is:
        `[ op( base(fft) ^ a ) ] ^ (1 / a)`

    where:
    - `op` is a unary or binary operation (e.g., addition, subtraction)
    - `a` is the power derived from gamma
    - `base` is the base operation on FFT
    - `fft` is the FFT of the audio signal

    Element of the form `base(fft)` is called _spectrum_, while
        `[ base(fft) ] ^ a`

    is called _FFT feature_, or simply _feature_.

    The base operation should be a positive real-valued function
    to ensure all that mapping `x ↦ x ^ a` is well-defined.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    transformations: Transformation = Field(..., description="FFT feature transformations")
    base_operation: UnaryTransformation = Field(
        default=energy,
        description="Base operation for FFT calculations. Default is the energy calculation: `||x||^2`",
    )

    @classmethod
    def from_gamma(cls, gamma: int) -> FFTTransformer:
        """
        Create an FFTTransformer from a gamma parameter.

        Args:
            gamma (int): Gamma parameter in the range [0, 100].

        Returns:
            FFTTransformer: Configured FFTTransformer instance.
        """
        assert 0 <= gamma <= MAX_TRANSFORMATION_GAMMA, f"Gamma must be in [0, {MAX_TRANSFORMATION_GAMMA}]"
        morpher = PowerMorpher(gamma / MAX_TRANSFORMATION_GAMMA)
        transformations = morpher.transformations
        return cls(transformations=transformations)

    def base(self, fft: np.ndarray) -> np.ndarray:
        """
        Base operation on the FFT values, called _spectrum_.
            `spectrum = base(fft)`

        The standard operation is energy calculation (hence the name),
        that is `||x_i||^2` for each FFT bin `x_i`.

        Args:
            fft (np.ndarray): Input FFT array.

        Returns:
            np.ndarray: Spectrum.
        """
        return self.base_operation(fft)

    def forward(self, spectrum: np.ndarray) -> np.ndarray:
        """
        Apply the forward `x ↦ x ^ a` transformation on an FFT feature.
        Spectrum is expected to be of the form `base(fft)`.

        Args:
            spectrum (np.ndarray): Input FFT spectrum array.

        Returns:
            np.ndarray: FFT feature.
        """
        return self.transformations.forward(spectrum)

    def backward(self, feature: np.ndarray) -> np.ndarray:
        """
        Apply the backward `x ↦ x ^ (1 / a)` transformation on an FFT feature.
        The feature is expected to be of the form `base(fft) ^ a`.

        Args:
            feature (np.ndarray): Input FFT feature array.

        Returns:
            np.ndarray: Spectrum.
        """
        return self.transformations.backward(feature)

    def unary(
        self,
        feature: np.ndarray,
        operation: UnaryTransformation,
    ) -> np.ndarray:
        """
        Apply a unary operation on an FFT feature with transformations.

        `[ op( feature ) ] ^ (1 / a)`
        """
        return self.transformations.unary(feature, operation)

    def binary(
        self,
        feature1: np.ndarray,
        feature2: np.ndarray,
        operation: BinaryTransformation,
    ) -> np.ndarray:
        """
        Apply a binary operation on two FFT features with transformations.

        """
        return self.transformations.binary(feature1, feature2, operation)

    def fft(
        self,
        audio: np.ndarray,
        fft_size: Optional[int] = None,
    ) -> np.ndarray:
        """
        Calculates FFT features from audio with transformations.
        Sends the audio through the base operation to obtain a power spectrum,
        and then applies the forward transformation.

        The feature is calculated as:
            `feature = base( fft(audio) ) ^ a`

        where a is the power derived from gamma, and fft(audio) is the (normalized) FFT
        of the audio signal.

        Args:
            audio (np.ndarray): Input audio array.
            fft_size (Optional[int]): Size of the FFT. If None, uses the length of the audio array.

        Returns:
            np.ndarray: Calculated FFT features.
        """
        fft: np.ndarray = calculate_fft(audio, fft_size)
        spectrum: np.ndarray = self.base(fft / fft.shape[0])
        return self.forward(spectrum)

    def add(
        self,
        feature1: np.ndarray,
        feature2: np.ndarray,
    ) -> np.ndarray:
        """
        A wrapper for binary addition of two FFT features with transformations.

        `[feature1 + feature2] ^ (1 / a)`
        """
        return self.binary(feature1, feature2, np.add)

    def subtract(
        self,
        feature1: np.ndarray,
        feature2: np.ndarray,
    ) -> np.ndarray:
        """
        A wrapper for binary subtraction of two FFT features with transformations.

        `[feature1 - feature2] ^ (1 / a)`
        """
        return self.binary(feature1, feature2, np.subtract)

    def multiply(
        self,
        feature: np.ndarray,
        scalar: float,
    ) -> np.ndarray:
        """
        Multiply an FFT feature by a scalar with transformations.

        `[ feature ⋅ α ] ^ (1 / a)`
        """
        return self.transformations.multiply(feature, scalar)
