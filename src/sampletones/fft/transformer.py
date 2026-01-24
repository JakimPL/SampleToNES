from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import MAX_TRANSFORMATION_GAMMA
from sampletones.structures.histogram import Histogram
from sampletones.types.array import ArrayOrScalar, Float, MultaryTransformation
from sampletones.utils.transformations.morpher import PowerMorpher
from sampletones.utils.transformations.transformation import Transformation

from .spectrum.method import SpectrumMethod
from .spectrum.spectrum import calculate_spectrum


class FFTTransformer(BaseModel):
    """
    A Transformation wrapper specifically for FFT features.

    Calculates FFT features on the spectrum and applies transformations
    of the form:
        `f(x) = x ^ a`

    where `a` is from [0.25, 4] depending on the gamma parameter. The `a` is mapped
    from gamma in [0, 100] to [0.25, 4] such that:
        - `gamma = 0   -> a = 0.25`  (flat features)
        - `gamma = 50  -> a = 1.0`   (standard energy)
        - `gamma = 100 -> a = 4.0`   (sharp features)

    More precisely, the general form of a transformation is:
        `[ op( spectrum ^ a ) ] ^ (1 / a)`

    where:
    - `op` is a unary or binary operation (e.g., addition, subtraction)
    - `a` is the power derived from gamma
    - `spectrum` is the result of the base operation on the FFT values.

    Elements of the form `spectrum ^ a` are called _FFT features_, or simply _features_.

    The spectrum should be a positive real-valued array,
    to ensure all that mapping `x ↦ x ^ a` is well-defined.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    transformations: Transformation = Field(..., description="FFT feature transformations")
    sample_rate: int = Field(
        ...,
        description="Sample rate used for FFT calculations.",
    )
    spectrum_method: SpectrumMethod = Field(
        default=SpectrumMethod.FFT,
        description="Method for computing the spectrum. Regular FFT is used by default.",
    )

    @classmethod
    def from_gamma(cls, gamma: int, sample_rate: int) -> FFTTransformer:
        """
        Create an FFTTransformer from a gamma parameter, and sample rate.

        Args:
            gamma (int): Gamma parameter in the range [0, 100].
            sample_rate (int): Sample rate for FFT calculations.

        Returns:
            FFTTransformer: Configured FFTTransformer instance.
        """
        assert 0 <= gamma <= MAX_TRANSFORMATION_GAMMA, f"Gamma must be in [0, {MAX_TRANSFORMATION_GAMMA}]"
        morpher = PowerMorpher(gamma / MAX_TRANSFORMATION_GAMMA)
        transformations = morpher.transformations
        return cls(transformations=transformations, sample_rate=sample_rate)

    def calculate_feature(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fft_size: Optional[int] = None,
    ) -> Histogram:
        """
        Calculate FFT features from audio, based on the provided spectrum method.
        Applies the forward transformation to the base spectrum.

        The feature is calculated as:
            `feature = spectrum ^ a`

        where `a` is the power derived from gamma.

        Args:
            audio (np.ndarray): Input audio array.
            sample_rate (int): Sample rate of the audio.
            fft_size (Optional[int]): Size of the FFT. If None, uses the length of the audio array.

        Returns:
            Histogram: Calculated FFT features.
        """
        spectrum: Histogram = calculate_spectrum(self.spectrum_method, audio, sample_rate, fft_size)
        return self.forward(spectrum)

    def forward(self, spectrum: Histogram) -> Histogram:
        """
        Apply the forward `x ↦ x ^ a` transformation on a spectrum.

        Args:
            spectrum (Histogram): Input FFT spectrum histogram.

        Returns:
            Histogram: FFT feature.
        """
        return spectrum.apply_with(self.transformations.forward)

    def backward(self, feature: Histogram) -> Histogram:
        """
        Apply the backward `x ↦ x ^ (1 / a)` transformation on an FFT feature.
        The feature is expected to be of the form `spectrum ^ a`.

        Args:
            feature (Histogram): Input FFT feature histogram.

        Returns:
            Histogram: Spectrum.
        """
        return feature.apply_with(self.transformations.backward)

    def apply(
        self,
        operation: MultaryTransformation[ArrayOrScalar],
        *features: Histogram,
    ) -> Histogram:
        """
        Apply an operation on an FFT feature with transformations.

        `[ op( feature ) ] ^ (1 / a)`

        Args:
            operation (MultaryTransformation): Operation to apply.
            *features: Input FFT features.

        Returns:
            Histogram: Resulting FFT feature.
        """
        return Histogram.apply(operation, *features)

    def reduce(
        self,
        operation: MultaryTransformation[ArrayOrScalar],
        *features: Histogram,
    ) -> Histogram:
        """
        Reduce multiple FFT features with an operation and transformations.

        `[ op( feature1, feature2, ..., featureN ) ] ^ (1 / a)`

        Args:
            operation (MultaryTransformation): Operation to reduce with.
            *features: Input FFT features.

        Returns:
            Histogram: Resulting FFT feature.
        """
        return Histogram.reduce(operation, *features)

    def add(
        self,
        *features: Histogram,
    ) -> Histogram:
        """
        A wrapper for binary addition of two FFT features with transformations.

        `[feature1 + feature2] ^ (1 / a)`

        Args:
            feature1 (Histogram): First FFT feature.
            feature2 (Histogram): Second FFT feature.
        """
        return self.reduce(np.add, *features)

    def subtract(
        self,
        feature1: Histogram,
        feature2: Histogram,
    ) -> Histogram:
        """
        A wrapper for binary subtraction of two FFT features with transformations.

        `[feature1 - feature2] ^ (1 / a)`

        Args:
            feature1 (Histogram): First FFT feature.
            feature2 (Histogram): Second FFT feature.
        """
        return self.apply(np.subtract, feature1, feature2)

    def multiply(
        self,
        feature: Histogram,
        scalar: Float,
    ) -> Histogram:
        """
        Multiply an FFT feature by a scalar with transformations.

        `[ feature ⋅ α ] ^ (1 / a)`
        """
        return self.reduce(
            np.multiply,
            feature,
            Histogram.from_constant(scalar, feature.edges),
        )
