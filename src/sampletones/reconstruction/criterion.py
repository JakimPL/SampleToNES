from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

from sampletones.configs import Config
from sampletones.ffts import Fragment, Window


@dataclass(frozen=True)
class Criterion:
    config: Config
    window: Window

    alpha: float = field(init=False)
    beta: float = field(init=False)

    def __post_init__(self):
        alpha, beta = self.get_loss_weights()
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "beta", beta)

    def __call__(
        self,
        fragment: Fragment,
        approximation: Fragment,
    ) -> np.ndarray:
        temporal_loss = self.temporal_loss(fragment.audio, approximation.audio)
        spectral_loss = self.spectral_loss(fragment.feature, approximation.feature)
        return self.combine_losses(spectral_loss, temporal_loss)

    def rmse(self, array1: np.ndarray, array2: np.ndarray, weights: Optional[np.ndarray] = None) -> np.ndarray:
        if weights is None:
            weights = np.ones_like(array1)
        else:
            weights = len(weights) * weights / np.sum(weights)

        return np.sqrt(np.mean(weights * np.square(array1 - array2), axis=-1))

    def temporal_loss(self, audio: np.ndarray, approximation: np.ndarray) -> np.ndarray:
        return self.rmse(audio, approximation, weights=None)

    def spectral_loss(
        self,
        fragment_feature: np.ndarray,
        approximation_feature: np.ndarray,
    ) -> np.ndarray:
        return self.rmse(fragment_feature, approximation_feature, weights=self.window.weights)

    def combine_losses(self, spectral_loss: np.ndarray, temporal_loss: np.ndarray) -> np.ndarray:
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
