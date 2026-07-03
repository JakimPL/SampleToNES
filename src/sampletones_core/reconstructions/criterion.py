from dataclasses import dataclass, field
from typing import Tuple, Union

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectralDistance, SpectrumMethod
from sampletones_core.constants.general import SPECTRUM_FLOOR
from sampletones_core.constants.spectrum import BINS_PER_OCTAVE, CQT_CUTOFF_FREQUENCY
from sampletones_core.fft import (
    FFTTransformer,
    Fragment,
    Window,
    calculate_weights_from_edges,
)
from sampletones_core.fft.cqt.frequencies import calculate_cqt_frequencies
from sampletones_core.fft.cqt.geometry import resolvable_bins
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp


@dataclass(frozen=True)
class Criterion:
    """
    Weighted spectral-and-temporal loss between a target fragment and candidate fragments.

    Under the constant-Q spectrum method, a bin resolves a frequency only when its wavelet fits
    within the ``signal_length`` samples of the target; bins below that floor drop to zero weight,
    so they neither reward nor penalize a candidate and the match rests on the bins both sides
    measure. Other spectrum methods resolve every bin uniformly and keep the full weighting.
    """

    config: Config
    window: Window
    signal_length: int

    alpha: float = field(init=False)
    beta: float = field(init=False)
    weights: xp.ndarray = field(init=False)
    no_weights: xp.ndarray = field(init=False)
    spectral_distance: SpectralDistance = field(init=False)
    divergence_beta: float = field(init=False)

    def __post_init__(self) -> None:
        alpha, beta = self.get_loss_weights()
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "beta", beta)

        metric = self.config.generation.metric
        object.__setattr__(self, "spectral_distance", SpectralDistance(metric.spectral_distance))
        object.__setattr__(self, "divergence_beta", float(metric.beta))

        no_weights = xp.ones(self.config.frame_length, dtype=xp.float32)
        weights = calculate_weights_from_edges(self._reference_edges(), metric.perceptual_exponent)
        weights = xp.asarray(weights)
        weights = len(weights) * weights / xp.sum(weights)
        weights = weights * self._reliability_mask(int(weights.shape[-1]))
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "no_weights", no_weights)

    def _reliability_mask(self, n_bins: int) -> xp.ndarray:
        """
        Per-bin factor that zeroes constant-Q bins the target signal is too short to resolve.

        A constant-Q bin needs a full wavelet of ``Q * sample_rate / frequency`` samples; over a
        target of ``signal_length`` samples only bins at or above ``reliable_frequency_floor`` reach
        that resolution. Zeroing the rest keeps the weighted loss on the bins both the target and the
        candidates measure. Other spectrum methods resolve every bin uniformly and keep a factor of one.

        Args:
            n_bins: Number of spectral bins in the feature.

        Returns:
            A length-``n_bins`` factor, one per resolvable bin and zero per under-resolved bin.
        """
        if self.config.library.spectrum_method != SpectrumMethod.CQT:
            return xp.ones(n_bins, dtype=xp.float32)

        frequencies = calculate_cqt_frequencies(n_bins, CQT_CUTOFF_FREQUENCY, BINS_PER_OCTAVE)
        resolvable = resolvable_bins(frequencies, self.config.library.sample_rate, self.signal_length, BINS_PER_OCTAVE)
        return xp.asarray(resolvable.astype(np.float32))

    def _reference_edges(self) -> np.ndarray:
        transformer = FFTTransformer.from_gamma(
            self.config.library.transformation_gamma,
            self.config.library.sample_rate,
            self.config.library.spectrum_method,
        )
        reference = transformer.calculate_feature(
            np.zeros(self.window.size, dtype=np.float32),
            self.config.library.sample_rate,
        )
        return np.asarray(reference.edges)

    def __call__(
        self,
        fragment: Fragment,
        approximation: Fragment,
    ) -> xp.ndarray:
        temporal_loss = self.temporal_loss(fragment.audio, approximation.audio)
        spectral_loss = self.spectral_loss(fragment.feature, approximation.feature)
        return self.combine_losses(spectral_loss, temporal_loss)

    def rmse(
        self,
        reference: Union[xp.ndarray, Histogram],
        candidates: Union[xp.ndarray, Histogram],
        with_weights: bool = True,
    ) -> xp.ndarray:
        if isinstance(reference, Histogram):
            reference = reference.values
        if isinstance(candidates, Histogram):
            candidates = candidates.values

        reference = xp.asarray(reference)
        candidates = xp.asarray(candidates)

        if reference.ndim != 1:
            raise ValueError("reference must be 1D")

        if candidates.ndim == 1:
            candidates = candidates[None, :]
        elif candidates.shape[1] != reference.shape[0]:
            raise ValueError(
                f"candidate width {candidates.shape[1]} does not match reference length {reference.shape[0]}"
            )

        weights = self.weights if with_weights else self.no_weights
        if weights.ndim == 1:
            weights = weights.reshape((1, -1))

        difference = xp.empty_like(candidates)
        xp.subtract(candidates, reference, out=difference)
        xp.square(difference, out=difference)
        xp.multiply(difference, weights, out=difference)
        mean = xp.mean(difference, axis=-1)
        return xp.sqrt(mean)

    def temporal_loss(self, audio: xp.ndarray, approximation: xp.ndarray) -> xp.ndarray:
        return self.rmse(audio, approximation, with_weights=False)

    def spectral_loss(
        self,
        feature: Union[xp.ndarray, Histogram],
        approximation_feature: Union[xp.ndarray, Histogram],
    ) -> xp.ndarray:
        reference, candidates, weights = self._prepare_spectral(feature, approximation_feature)

        match self.spectral_distance:
            case SpectralDistance.SQUARED:
                numerator = xp.sqrt(xp.sum(weights * (candidates - reference) ** 2, axis=-1))
                denominator = xp.sqrt(xp.sum(weights * reference**2, axis=-1))
            case SpectralDistance.ABSOLUTE:
                numerator = xp.sum(weights * xp.abs(candidates - reference), axis=-1)
                denominator = xp.sum(weights * reference, axis=-1)
            case SpectralDistance.BETA_DIVERGENCE:
                numerator = xp.sum(weights * self._beta_divergence(reference, candidates), axis=-1)
                denominator = xp.sum(weights * reference, axis=-1)
            case _:
                raise ValueError(f"Unsupported spectral distance: {self.spectral_distance}")

        return numerator / (denominator + SPECTRUM_FLOOR)

    def combine_losses(self, spectral_loss: xp.ndarray, temporal_loss: xp.ndarray) -> xp.ndarray:
        return self.alpha * spectral_loss + self.beta * temporal_loss

    def _prepare_spectral(
        self,
        feature: Union[xp.ndarray, Histogram],
        approximation_feature: Union[xp.ndarray, Histogram],
    ) -> Tuple[xp.ndarray, xp.ndarray, xp.ndarray]:
        reference = feature.values if isinstance(feature, Histogram) else feature
        candidates = (
            approximation_feature.values if isinstance(approximation_feature, Histogram) else approximation_feature
        )

        reference = xp.asarray(reference)
        candidates = xp.asarray(candidates)

        if reference.ndim != 1:
            raise ValueError("reference must be 1D")

        if candidates.ndim == 1:
            candidates = candidates[None, :]
        elif candidates.shape[1] != reference.shape[0]:
            raise ValueError(
                f"candidate width {candidates.shape[1]} does not match reference length {reference.shape[0]}"
            )

        weights = self.weights
        if weights.ndim == 1:
            weights = weights.reshape((1, -1))

        return reference.reshape((1, -1)), candidates, weights

    def _beta_divergence(self, reference: xp.ndarray, candidates: xp.ndarray) -> xp.ndarray:
        reference = reference + SPECTRUM_FLOOR
        candidates = candidates + SPECTRUM_FLOOR
        beta = self.divergence_beta

        if beta == 1.0:
            return reference * (xp.log(reference) - xp.log(candidates)) + (candidates - reference)

        if beta == 0.0:
            ratio = reference / candidates
            return ratio - xp.log(ratio) - 1.0

        return (
            reference**beta + (beta - 1.0) * candidates**beta - beta * reference * candidates ** (beta - 1.0)
        ) / (beta * (beta - 1.0))

    def get_loss_weights(self) -> Tuple[float, float]:
        alpha = self.config.generation.weights.spectral_loss_weight
        beta = self.config.generation.weights.temporal_loss_weight
        weights = alpha, beta

        if not all(isinstance(weight, float) and weight >= 0.0 for weight in weights):
            raise ValueError("Loss weights must be non-negative numbers")

        total = sum(weights)
        if total == 0:
            raise ValueError("At least one of the loss weights must be greater than zero")

        return alpha / total, beta / total
