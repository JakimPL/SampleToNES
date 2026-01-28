from __future__ import annotations

from typing import List, Optional, Self, Sequence, Union, overload

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE
from sampletones.constants.general import MAX_TRANSFORMATION_GAMMA
from sampletones.structures.histogram import Histogram
from sampletones.types.array import (
    Array,
    ArrayOrNumeric,
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

    Calculates FFT features on the spectrum and sends them to the feature space.
    Features are of the form:

        `f(x) = x ^ a`

    The feature space allows to shape the spectrum, either to flatten it or to sharpen its peaks.

    The exponent `a` is a value from [0.25, 4], which depends on the `gamma` parameter in [0, 100].
    The mapping from `gamma` to `a` is as follows:
        - `gamma = 0   -> a = 0.25`  (flat features)
        - `gamma = 50  -> a = 1.0`   (standard energy)
        - `gamma = 100 -> a = 4.0`   (sharp features)

    FFTTransformer allows transforming features by applying operations in the original spectrum space,
    and then mapping the result back to the feature space. More precisely, the general form of
    a composed transformation is:

        `[ op( spectrum ^ (1 / a) ) ] ^ a`

    where:
    - `op` is a unary or binary operation (e.g., addition, subtraction)
    - `a` is the power derived from gamma
    - `spectrum` is the result of the base operation on the FFT values.

    Elements of the form `spectrum ^ a` are called _FFT features_, or simply _features_.

    The spectrum should be a positive real-valued array, to ensure all that mapping:

        `x ↦ x ^ a`

    is well-defined. The condition of non-negativity is enforced only during spectrum calculation.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, use_enum_values=True)

    transformation: Transformation = Field(..., description="FFT feature transformations")
    sample_rate: int = Field(
        ...,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
        description="Sample rate used for FFT calculations.",
    )
    spectrum_method: SpectrumMethod = Field(
        default=SpectrumMethod.FFT,
        description="Method for computing the spectrum. Regular FFT is used by default.",
    )

    @classmethod
    def from_gamma(cls, gamma: int, sample_rate: int) -> Self:
        """
        Create an FFTTransformer from a gamma parameter, and sample rate.

        Args:
            gamma (int): Gamma parameter in the range [0, 100].
            sample_rate (int): Sample rate for FFT calculations.

        Returns:
            Self: Configured FFTTransformer instance.
        """
        assert 0 <= gamma <= MAX_TRANSFORMATION_GAMMA, f"Gamma must be in [0, {MAX_TRANSFORMATION_GAMMA}]"
        morpher = PowerMorpher(gamma=gamma / MAX_TRANSFORMATION_GAMMA)
        transformation = morpher.transformation
        return cls(transformation=transformation, sample_rate=sample_rate)

    def calculate_spectrum(
        self,
        audio: np.ndarray,
        sample_rate: int,
        fft_size: Optional[int] = None,
    ) -> Histogram:
        """
        Calculate the FFT spectrum from audio, based on the provided spectrum method.

        Args:
            audio (np.ndarray): Input audio array.
            sample_rate (int): Sample rate of the audio.
            fft_size (Optional[int]): Size of the FFT. If None, uses the length of the audio array.

        Returns:
            Histogram: Calculated FFT spectrum.

        Raises:
            ValueError: If the calculated spectrum contains negative values.
        """
        spectrum: Histogram = calculate_spectrum(self.spectrum_method, audio, sample_rate, fft_size)
        if not np.all(spectrum.values >= 0):
            raise ValueError("FFT spectrum contains negative values")

        return spectrum

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

        Raises:
            ValueError: If the calculated spectrum contains negative values.
        """
        spectrum: Histogram = self.calculate_spectrum(audio, sample_rate, fft_size)
        return self.forward(spectrum)

    @overload
    def forward(self, spectrum: Histogram) -> Histogram: ...

    @overload
    def forward(self, spectrum: ArrayOrNumeric) -> ArrayOrNumeric: ...

    def forward(self, spectrum: Union[ArrayOrNumeric, Histogram]) -> Union[ArrayOrNumeric, Histogram]:
        """
        Apply the forward `x ↦ x ^ a` transformation on a spectrum/array/scalar.

        Args:
            spectrum (Union[ArrayOrNumeric, Histogram]): Input FFT spectrum histogram, array, or scalar.

        Returns:
            Union[ArrayOrNumeric, Histogram]: FFT feature (same type as input).

        Raises:
            TypeError: If the input is not a Histogram or Array/Numeric instance.
        """
        if isinstance(spectrum, Histogram):
            return spectrum.apply_with(self.transformation.forward)

        if isinstance(spectrum, ArrayOrScalarClasses):
            return self.transformation.forward(spectrum)

        raise TypeError("Input must be a Histogram or Array/Numeric instance")

    @overload
    def backward(self, feature: Histogram) -> Histogram: ...

    @overload
    def backward(self, feature: ArrayOrNumeric) -> ArrayOrNumeric: ...

    def backward(self, feature: Union[ArrayOrNumeric, Histogram]) -> Union[ArrayOrNumeric, Histogram]:
        """
        Apply the backward `x ↦ x ^ (1 / a)` transformation on an FFT feature/array/scalar.
        The feature is expected to be of the form `spectrum ^ a`.

        Args:
            feature (Union[ArrayOrNumeric, Histogram]): Input FFT feature histogram, array, or scalar.

        Returns:
            Union[ArrayOrNumeric, Histogram]: Spectrum (same type as input).

        Raises:
            TypeError: If the input is not a Histogram or Array/Numeric instance.
        """
        if isinstance(feature, Histogram):
            return feature.apply_with(self.transformation.backward)

        if isinstance(feature, ArrayOrScalarClasses):
            return self.transformation.backward(feature)

        raise TypeError("Input must be a Histogram or Array/Numeric instance")

    def compose_function(
        self,
        operation: MultaryTransformation[ArrayOrNumeric],
    ) -> MultaryTransformation[ArrayOrNumeric]:
        """
        A wrapper for composing an operation on FFT features with transformations.

        The composed function is of the form:

            `[ op( x₁ ^ (1 / a), x₂ ^ (1 / a), ..., xₙ ^ (1 / a) ) ] ^ a`

        Args:
            operation (MultaryTransformation[ArrayOrNumeric]): Operation to compose.

        Returns:
            MultaryTransformation[ArrayOrNumeric]: Composed transformation function.
        """
        return self.transformation.compose_function(operation)

    def apply(
        self,
        operation: MultaryTransformation[ArrayOrNumeric],
        *features: Histogram,
    ) -> Histogram:
        """
        Apply an operation on an FFT feature with transformations.

            `[ op( feature ^ (1 / a) ) ] ^ a`

        Args:
            operation (MultaryTransformation[ArrayOrNumeric]): Operation to apply.
            *features (Histogram): Input FFT features.

        Returns:
            Histogram: Resulting FFT feature.

        Raises:
            TypeError: If any of the features is not a Histogram.
        """
        if not all(isinstance(feature, Histogram) for feature in features):
            raise TypeError("All features must be Histogram instances")

        function = self.transformation.compose_function(operation)
        return Histogram.apply(function, *features)

    def reduce(
        self,
        operation: MultaryTransformation[ArrayOrNumeric],
        *features: Histogram,
    ) -> Histogram:
        """
        Reduce multiple FFT features with an operation and transformations.

            `[ op( feature₁ ^ (1 / a), feature₂ ^ (1 / a), ..., featureₙ ^ (1 / a) ) ] ^ a`

        Args:
            operation (MultaryTransformation[ArrayOrNumeric]): Operation to reduce with.
            *features (Histogram): Input FFT features.

        Returns:
            Histogram: Resulting FFT feature.

        Raises:
            TypeError: If any of the features is not a Histogram.
        """
        if not all(isinstance(feature, Histogram) for feature in features):
            raise TypeError("All features must be Histogram instances")

        function = self.transformation.compose_function(operation)
        return Histogram.reduce(function, *features)

    def to_features(self, features_or_scalars: Sequence[Union[Numeric, Histogram]]) -> List[Histogram]:
        """
        Convert a list of features/scalars to FFT features.

        Sends constants to the feature space.

        Args:
            features_or_scalars (Sequence[Union[Numeric, Histogram]]): Input FFT features/scalars.

        Returns:
            List[Histogram]: Converted FFT features.

        Raises:
            TypeError: If there are no histograms in the input.
            TypeError: If any of the features is neither a Histogram nor a numeric scalar.
            ValueError: If Histogram features have inconsistent edges.
        """
        histograms: List[Histogram] = [feature for feature in features_or_scalars if isinstance(feature, Histogram)]
        if not histograms:
            raise TypeError("At least one feature must be a Histogram instance")

        if any(not isinstance(feature, (Histogram, *NumericClasses)) for feature in features_or_scalars):
            raise TypeError("All features must be Histogram instances or numeric scalars")

        edges: Array = histograms[0].edges
        if not all(np.array_equal(histogram.edges, edges) for histogram in histograms):
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

            `[ feature₁ ^ (1 / a) + feature₂ ^ (1 / a) + ... + featureₙ ^ (1 / a) ] ^ a`

        Scalars are transformed to the feature space before addition.

        Args:
            *features_or_scalars (Union[Numeric, Histogram]): Input FFT features or scalars.

        Returns:
            Histogram: Resulting FFT feature.
        """
        features: List[Histogram] = self.to_features(features_or_scalars)
        return self.reduce(lambda feature1, feature2: feature1 + feature2, *features)

    def subtract(
        self,
        feature_or_scalar1: Union[Numeric, Histogram],
        feature_or_scalar2: Union[Numeric, Histogram],
    ) -> Histogram:
        """
        A wrapper for binary subtraction of two FFT features with transformations.

            `[ |feature₁ ^ (1 / a) - feature₂ ^ (1 / a)| ] ^ a`

        Absolute difference is used to ensure non-negativity.

        Scalars are transformed to the feature space before subtraction.

        Args:
            feature_or_scalar1 (Union[Numeric, Histogram]): First FFT feature or scalar.
            feature_or_scalar2 (Union[Numeric, Histogram]): Second FFT feature or scalar.

        Returns:
            Histogram: Resulting FFT feature.
        """
        feature1, feature2 = self.to_features((feature_or_scalar1, feature_or_scalar2))
        return self.apply(lambda feature1, feature2: np.abs(feature1 - feature2), feature1, feature2)

    def multiply(self, *features_or_scalars: Union[Numeric, Histogram]) -> Histogram:
        """
        Multiply an FFT feature by another features/scalars with transformations.

            `[ feature₁ ^ (1 / a) ⋅ feature₂ ^ (1 / a) ⋅ ... ⋅ featureₙ ^ (1 / a) ] ^ a`

        Scalars are transformed to the feature space before multiplication.

        Args:
            *features_or_scalars (Union[Numeric, Histogram]): Input FFT features or scalars.

        Returns:
            Histogram: Resulting FFT feature.
        """
        features: List[Histogram] = self.to_features(features_or_scalars)
        return self.reduce(lambda feature1, feature2: feature1 * feature2, *features)

    def divide(
        self,
        feature_or_scalar1: Union[Numeric, Histogram],
        feature_or_scalar2: Union[Numeric, Histogram],
    ) -> Histogram:
        """
        Divide an FFT feature by another feature with transformations.

            `[ feature₁ ^ (1 / a) ÷ feature₂ ^ (1 / a) ] ^ a`

        Args:
            feature_or_scalar1 (Union[Numeric, Histogram]): Numerator FFT feature or scalar.
            feature_or_scalar2 (Union[Numeric, Histogram]): Denominator FFT feature or scalar.

        Returns:
            Histogram: Resulting FFT feature.
        """
        feature1, feature2 = self.to_features((feature_or_scalar1, feature_or_scalar2))
        return self.apply(lambda feature1, feature2: feature1 / feature2, feature1, feature2)

    def mean(
        self,
        features: Sequence[Histogram],
    ) -> Histogram:
        """
        Calculate the mean of multiple FFT features with transformations.

            `[ mean(feature₁ ^ (1 / a), feature₂ ^ (1 / a), ..., featureₙ ^ (1 / a)) ] ^ a`

        Requires all edges to be consistent.

        Args:
            features (Sequence[Histogram]): Input FFT features.

        Returns:
            Histogram: Mean FFT feature.

        Raises:
            ValueError: If no features are provided.
            ValueError: If Histogram features have inconsistent edges.
            TypeError: If any of the features is not a Histogram.
        """
        if not features:
            raise ValueError("At least one feature is required to compute the mean")

        divisor = self.forward(len(features))
        return self.reduce(np.add, *features).apply_with(lambda x: np.divide(x, divisor, out=x, casting="unsafe"))
