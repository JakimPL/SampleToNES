from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np
from sklearn.metrics import root_mean_squared_error

from configs import Config
from ffts import Window
from instructions import Instruction
from library import Fragment


@dataclass(frozen=True)
class Criterion:
    config: Config
    window: Window

    alpha: float = field(init=False)
    beta: float = field(init=False)
    gamma: float = field(init=False)

    def __post_init__(self):
        alpha, beta, gamma = self.get_loss_weights()
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "beta", beta)
        object.__setattr__(self, "gamma", gamma)

    def __call__(
        self,
        fragment: Fragment,
        approximation: Fragment,
        instruction: Instruction,
        previous_instruction: Optional[Instruction] = None,
    ) -> float:
        temporal_loss = self.temporal_loss(fragment.audio, approximation.audio)
        spectral_loss = self.spectral_loss(fragment.feature, approximation.feature)
        continuity_loss = self.continuity_loss(instruction, previous_instruction)
        return self.combine_losses(spectral_loss, temporal_loss, continuity_loss)

    def temporal_loss(self, audio: np.ndarray, approximation: np.ndarray) -> float:
        return root_mean_squared_error(audio, approximation)

    def continuity_loss(self, instruction: Instruction, previous_instruction: Optional[Instruction]) -> float:
        return 0.0 if previous_instruction is None else instruction.distance(previous_instruction)

    def spectral_loss(
        self,
        fragment_feature: np.ndarray,
        approximation_feature: np.ndarray,
    ) -> float:
        return float(np.average(np.square(fragment_feature - approximation_feature), weights=self.window.weights))

    def combine_losses(self, spectral_loss: float, temporal_loss: float, continuity_loss: float) -> float:
        return self.alpha * spectral_loss + self.beta * temporal_loss + self.gamma * continuity_loss

    def get_loss_weights(self) -> Tuple[float, float, float]:
        alpha = self.config.generation.weights.spectral_loss_weight
        beta = self.config.generation.weights.temporal_loss_weight
        gamma = self.config.generation.weights.continuity_loss_weight
        weights = alpha, beta, gamma

        assert all(
            isinstance(weight, float) and weight >= 0.0 for weight in weights
        ), "Loss weights must be non-negative numbers."
        total = sum(weights)
        if total == 0:
            raise ValueError("At least one of the loss weights must be greater than zero.")

        return alpha / total, beta / total, gamma / total
