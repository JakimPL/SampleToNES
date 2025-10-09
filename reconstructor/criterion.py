from typing import Optional, Tuple

import numpy as np
from sklearn.metrics import root_mean_squared_error

from config import Config
from ffts.fft import calculate_log_arfft, calculate_weights
from ffts.window import Window
from instructions.instruction import Instruction


class Criterion:
    def __init__(self, config: Config, window: Window) -> None:
        self.config: Config = config
        self.fragment_length: Optional[int] = None
        self.window: Window = window

        alpha, beta, gamma = self.get_loss_weights()
        self.alpha: float = alpha
        self.beta: float = beta
        self.gamma: float = gamma

        # self.library: FFTLibrary = FFTLibrary.load(self.config.library_path)
        # self.library.update(config, window)

    def __call__(
        self,
        audio: np.ndarray,
        approximation: np.ndarray,
        instruction: Instruction,
        previous_instruction: Optional[Instruction] = None,
    ) -> float:
        audio_frame = self.window.get_frame_from_window(audio)
        frame = self.window.get_frame_from_window(approximation)
        spectral_loss = self.spectral_loss(audio, approximation)
        temporal_loss = self.temporal_loss(audio_frame, frame)
        continuity_loss = self.continuity_loss(instruction, previous_instruction)

        return self.combine_losses(spectral_loss, temporal_loss, continuity_loss)

    def temporal_loss(self, audio: np.ndarray, approximation: np.ndarray) -> float:
        return root_mean_squared_error(audio, approximation)

    def continuity_loss(self, instruction: Instruction, previous_instruction: Optional[Instruction]) -> float:
        return 0.0 if previous_instruction is None else instruction.distance(previous_instruction)

    def spectral_loss(
        self,
        audio: np.ndarray,
        approximation: np.ndarray,
    ) -> float:
        fragment_spectrum = calculate_log_arfft(audio)
        approximation_spectrum = calculate_log_arfft(approximation)
        weights = calculate_weights(self.window.size, self.config.sample_rate)
        return np.average(np.square(fragment_spectrum - approximation_spectrum), weights=weights)

    def combine_losses(self, spectral_loss: float, temporal_loss: float, continuity_loss: float) -> float:
        # print(f"Spectral Loss: {spectral_loss}, Temporal Loss: {temporal_loss}")
        return self.alpha * spectral_loss + self.beta * temporal_loss + self.gamma * continuity_loss

    def get_loss_weights(self) -> Tuple[float, float, float]:
        alpha = self.config.spectral_loss_weight
        beta = self.config.temporal_loss_weight
        gamma = self.config.continuity_loss_weight
        weights = alpha, beta, gamma

        assert all(
            isinstance(weight, float) and weight >= 0.0 for weight in weights
        ), "Loss weights must be non-negative numbers."
        total = sum(weights)
        if total == 0:
            raise ValueError("At least one of the loss weights must be greater than zero.")

        return alpha / total, beta / total, gamma / total
