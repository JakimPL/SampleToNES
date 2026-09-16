from typing import Tuple, Union

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.array import xp

from .metric import SpectralMetric
from .spectral import calculate_spectral_loss, weighted_reference_energy
from .temporal import calculate_expected_temporal_loss, calculate_temporal_loss
from .weights import calculate_spectral_weights


class Criterion:
    """
    Weighted spectral-and-temporal loss between a target fragment and candidate fragments.

    Composes the three concerns the loss is made of — the per-bin weighting policy
    (`weights`), the spectral distance (`spectral`), and the level-normalized temporal
    distance (`temporal`) — and blends the two losses with the configured
    spectral/temporal weights. Under the constant-Q spectrum method, bins the target
    signal is too short to resolve carry zero weight, so the match rests on the bins
    both sides measure.
    """

    def __init__(self, config: Config, window: Window, signal_length: int) -> None:
        self.alpha, self.beta = _validate_loss_blend(config)

        metric = config.generation.metric
        self.metric = SpectralMetric.from_config(metric)
        self.temporal_level_floor = float(metric.temporal_level_floor)
        self.weights = calculate_spectral_weights(config, window, signal_length)

    def spectral_loss(
        self,
        feature: Union[xp.ndarray, Histogram],
        approximation_feature: Union[xp.ndarray, Histogram],
    ) -> xp.ndarray:
        """
        Weighted spectral distance between the target feature and candidate features.

        Args:
            feature: Target feature, as a histogram or its values.
            approximation_feature: Candidate features, as a histogram or stacked values.

        Returns:
            One loss per candidate.
        """
        return calculate_spectral_loss(
            _feature_values(feature),
            _feature_values(approximation_feature),
            self.weights,
            metric=self.metric,
        )

    def reference_energy(self, feature: Union[xp.ndarray, Histogram]) -> xp.ndarray:
        """
        Weighted energy the target feature holds, the scale its spectral loss is measured against.

        Args:
            feature: Target feature, as a histogram or its values.

        Returns:
            The target's weighted energy.
        """
        return weighted_reference_energy(
            _feature_values(feature),
            self.weights,
            distance=self.metric.distance,
        )

    def temporal_loss(
        self,
        audio: xp.ndarray,
        approximation: xp.ndarray,
    ) -> xp.ndarray:
        """
        Level-normalized RMS difference between the target and candidate waveforms.

        Frames quieter than the configured temporal level floor (by default the
        quietest playable volume relative to the working level) normalize as if at
        that floor, keeping costs bounded for near-silent frames.

        Args:
            audio: Target waveform.
            approximation: Candidate waveforms, one candidate per row.

        Returns:
            One loss per candidate.
        """
        return calculate_temporal_loss(
            audio,
            approximation,
            level_floor=self.temporal_level_floor,
        )

    def expected_temporal_loss(
        self,
        audio: xp.ndarray,
        expectation: Union[float, xp.ndarray],
        variance: Union[float, xp.ndarray],
    ) -> xp.ndarray:
        """
        Level-normalized RMS difference expected between the target and candidates known up to a
        spread about the waveform they are expected to render.

        Args:
            audio: Target waveform.
            expectation: The expected waveforms, one candidate per row, or one waveform or level
                every candidate shares.
            variance: The per-sample variance of each candidate, or one variance every candidate
                shares.

        Returns:
            One loss per candidate.
        """
        return calculate_expected_temporal_loss(
            audio,
            expectation,
            variance,
            level_floor=self.temporal_level_floor,
        )

    def combine_losses(
        self,
        spectral_loss: Union[float, xp.ndarray],
        temporal_loss: Union[float, xp.ndarray],
    ) -> xp.ndarray:
        return self.alpha * spectral_loss + self.beta * temporal_loss


def _feature_values(feature: Union[xp.ndarray, Histogram]) -> xp.ndarray:
    if isinstance(feature, Histogram):
        return feature.values

    return feature


def _validate_loss_blend(config: Config) -> Tuple[float, float]:
    """
    Normalized spectral/temporal blend weights of the configuration.

    Args:
        config: Configuration carrying the loss weights.

    Returns:
        The spectral and temporal weights, scaled to sum to one.

    Raises:
        ValueError: If a loss weight is negative or of a non-float type.
        ValueError: If both loss weights are zero.
    """
    alpha = config.generation.weights.spectral_loss_weight
    beta = config.generation.weights.temporal_loss_weight
    weights = alpha, beta

    if not all(isinstance(weight, float) and weight >= 0.0 for weight in weights):
        raise ValueError("Loss weights must be non-negative numbers")

    total = sum(weights)
    if total == 0:
        raise ValueError("At least one of the loss weights must be greater than zero")

    return alpha / total, beta / total
