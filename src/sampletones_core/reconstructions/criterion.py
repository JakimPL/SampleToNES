from dataclasses import dataclass, field
from typing import Tuple, Union

import numpy as np

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectralDistance
from sampletones_core.constants.general import SPECTRUM_FLOOR
from sampletones_core.fft import (
    FFTTransformer,
    Fragment,
    Window,
    calculate_weights_from_edges,
)
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp


@dataclass(frozen=True)
class Criterion:
    config: Config
    window: Window

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
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "no_weights", no_weights)

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
