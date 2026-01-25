from __future__ import annotations

from typing import List, Optional, Sequence, Union, overload

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import MAX_TRANSFORMATION_GAMMA
from sampletones.structures.histogram import Histogram
from sampletones.types.array import (
    Array,
    ArrayOrScalar,
    ArrayOrScalarClasses,
    MultaryTransformation,
    Numeric,
    NumericClasses,
)
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

    def calculate_spectrum(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fft_size: Optional[int] = None,
    ) -> Histogram:
        return calculate_spectrum(self.spectrum_method, audio, sample_rate, fft_size)

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
        spectrum: Histogram = self.calculate_spectrum(audio, sample_rate, fft_size)
        return self.forward(spectrum)

    @overload
    def forward(self, spectrum: Histogram) -> Histogram: ...

    @overload
    def forward(self, spectrum: ArrayOrScalar) -> ArrayOrScalar: ...

    def forward(self, spectrum: Union[ArrayOrScalar, Histogram]) -> Union[ArrayOrScalar, Histogram]:
        """
        Apply the forward `x ↦ x ^ a` transformation on a spectrum/array/scalar.

        Args:
            spectrum: Input FFT spectrum histogram.

        Returns:
            FFT feature.

        Raises:
            TypeError: If the input is not a Histogram or Array/Numeric instance.
        """
        if isinstance(spectrum, Histogram):
            return spectrum.apply_with(self.transformations.forward)

        if isinstance(spectrum, ArrayOrScalarClasses):
            return self.transformations.forward(spectrum)

        raise TypeError("Input must be a Histogram or Array/Numeric instance")

    @overload
    def backward(self, feature: Histogram) -> Histogram: ...

    @overload
    def backward(self, feature: ArrayOrScalar) -> ArrayOrScalar: ...

    def backward(self, feature: Union[ArrayOrScalar, Histogram]) -> Union[ArrayOrScalar, Histogram]:
        """
        Apply the backward `x ↦ x ^ (1 / a)` transformation on an FFT feature/array/scalar.
        The feature is expected to be of the form `spectrum ^ a`.

        Args:
            feature: Input FFT feature histogram.

        Returns:
            Spectrum.

        Raises:
            TypeError: If the input is not a Histogram or Array/Numeric instance.
        """
        if isinstance(feature, Histogram):
            return feature.apply_with(self.transformations.backward)

        if isinstance(feature, ArrayOrScalarClasses):
            return self.transformations.backward(feature)

        raise TypeError("Input must be a Histogram or Array/Numeric instance")

    def compose_function(
        self,
        operation: MultaryTransformation[ArrayOrScalar],
    ) -> MultaryTransformation[ArrayOrScalar]:
        """
        A wrapper for composing an operation on FFT features with transformations.

        The composed function is of the form:

            `f[ op( f^-1(x_1), f^-1(x_2), ..., f^-1(x_n) ) ]`

        where `f` is the forward transformation and `f^-1` is the backward transformation.

        Args:
            operation (MultaryTransformation): Operation to compose.
        """
        return self.transformations.compose_function(operation)

    def apply(
        self,
        operation: MultaryTransformation[ArrayOrScalar],
        *features: Histogram,
    ) -> Histogram:
        """
        Apply an operation on an FFT feature with transformations.

            `[ op( feature ) ] ^ (1 / a)`

        Args:
            operation: Operation to apply.
            *features: Input FFT features.

        Returns:
            Resulting FFT feature.

        Raises:
            TypeError: If any of the features is not a Histogram.
        """
        if not all(isinstance(feature, Histogram) for feature in features):
            raise TypeError("All features must be Histogram instances")

        function = self.transformations.compose_function(operation)
        return Histogram.apply(function, *features)

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
            Resulting FFT feature.

        Raises:
            TypeError: If any of the features is not a Histogram.
        """
        if not all(isinstance(feature, Histogram) for feature in features):
            raise TypeError("All features must be Histogram instances")

        function = self.transformations.compose_function(operation)
        return Histogram.reduce(function, *features)

    def to_features(self, features_or_scalars: Sequence[Union[Numeric, Histogram]]) -> List[Histogram]:
        """
        Convert a list of features/scalars to FFT features.

        Args:
            *features_or_scalars: Input FFT features/scalars.

        Returns:
            Converted FFT features.

        Raises:
            TypeError: If at least one of the features is not a Histogram.
            ValueError: If Histogram features have inconsistent edges.
        """
        if not any(isinstance(feature, Histogram) for feature in features_or_scalars):
            raise TypeError("At least one feature must be a Histogram instance")

        edges: Array = [feature.edges for feature in features_or_scalars if isinstance(feature, Histogram)][0]
        if not all(
            isinstance(feature, Histogram) and np.array_equal(feature.edges, edges)
            for feature in features_or_scalars
            if isinstance(feature, Histogram)
        ):
            raise ValueError("All Histogram features must have the same edges")

        features: List[Histogram] = [
            self.forward(Histogram.from_constant(feature, edges)) if isinstance(feature, NumericClasses) else feature
            for feature in features_or_scalars
        ]

        return features

    def add(
        self,
        *features_or_scalars: Union[Numeric, Histogram],
    ) -> Histogram:
        """
        A wrapper for binary addition of FFT features/scalars with transformations.

            `[ feature1 + feature2 + ... + featureN ] ^ (1 / a)`

        Args:
            features_or_scalars: Input FFT features/scalars.

        Returns:
            Resulting FFT feature.
        """
        features: List[Histogram] = self.to_features(features_or_scalars)
        return self.reduce(np.add, *features)

    def subtract(
        self,
        feature1: Histogram,
        feature2: Histogram,
    ) -> Histogram:
        """
        A wrapper for binary subtraction of two FFT features with transformations.

            `[ feature1 - feature2 ] ^ (1 / a)`

        Args:
            feature1 (Histogram): First FFT feature.
            feature2 (Histogram): Second FFT feature.
        """
        return self.apply(np.subtract, feature1, feature2)

    def multiply(self, *features_or_scalars: Union[Numeric, Histogram]) -> Histogram:
        """
        Multiply an FFT feature by another features/scalars with transformations.

            `[ feature1 ⋅ feature2 ⋅ ... ⋅ featureN ] ^ (1 / a)`

        Args:
            *features: Input FFT features/scalars.

        Returns:
            Histogram: Resulting FFT feature.

        Raises:
            TypeError: If at least one of the features is not a Histogram.
        """
        features: List[Histogram] = self.to_features(features_or_scalars)
        return self.reduce(np.multiply, *features)

    def mean(
        self,
        features: Sequence[Histogram],
    ) -> Histogram:
        """
        Calculate the mean of multiple FFT features with transformations.

            `[ mean(feature1, feature2, ..., featureN) ] ^ (1 / a)`

        Args:
            features: Input FFT features.

        Returns:
            Histogram: Mean FFT feature.

        Raises:
            ValueError: If no features are provided.
        """
        if not features:
            raise ValueError("At least one feature is required to compute the mean")

        divisor = self.forward(np.float32(len(features)))
        return self.reduce(np.add, *features).apply_with(lambda x: x / divisor)
