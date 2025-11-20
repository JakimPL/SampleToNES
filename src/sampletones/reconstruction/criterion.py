from dataclasses import dataclass, field
from typing import Tuple

from sampletones import xp
from sampletones.configs import Config
from sampletones.ffts import Fragment, Window


@dataclass(frozen=True)
class Criterion:
    config: Config
    window: Window

    alpha: float = field(init=False)
    beta: float = field(init=False)
    weights: xp.ndarray = field(init=False)
    no_weights: xp.ndarray = field(init=False)

    def __post_init__(self):
        alpha, beta = self.get_loss_weights()
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "beta", beta)

        no_weights = xp.ones(self.config.frame_length, dtype=xp.float32)
        weights = xp.asarray(self.window.weights)
        weights = len(weights) * weights / xp.sum(weights)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "no_weights", no_weights)

    def __call__(
        self,
        fragment: Fragment,
        approximation: Fragment,
    ) -> xp.ndarray:
        temporal_loss = self.temporal_loss(fragment.audio, approximation.audio)
        spectral_loss = self.spectral_loss(fragment.feature, approximation.feature)
        return self.combine_losses(spectral_loss, temporal_loss)

    def rmse(self, reference: xp.ndarray, candidates: xp.ndarray, with_weights: bool = True) -> xp.ndarray:
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
        feature: xp.ndarray,
        approximation_feature: xp.ndarray,
    ) -> xp.ndarray:
        return self.rmse(feature, approximation_feature, with_weights=True)

    def combine_losses(self, spectral_loss: xp.ndarray, temporal_loss: xp.ndarray) -> xp.ndarray:
        return self.alpha * spectral_loss + self.beta * temporal_loss

    def get_loss_weights(self) -> Tuple[float, float]:
        alpha = self.config.generation.weights.spectral_loss_weight
        beta = self.config.generation.weights.temporal_loss_weight
        weights = alpha, beta

        assert all(
            isinstance(weight, float) and weight >= 0.0 for weight in weights
        ), "Loss weights must be non-negative numbers."
        total = sum(weights)
        if total == 0:
            raise ValueError("At least one of the loss weights must be greater than zero.")

        return alpha / total, beta / total
