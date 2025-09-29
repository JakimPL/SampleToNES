from os import name
from typing import List, Optional, Union

import numpy as np
import scipy.fft
from scipy.signal import get_window
from sklearn.metrics import root_mean_squared_error

from config import Config
from constants import MAX_FREQUENCY, MIN_FREQUENCY
from reconstructor.state import ReconstructionState


class Loss:
    def __init__(self, generator_name: str, config: Config):
        self.generator_name: str = generator_name
        self.config: Config = config
        self.fragment_length: Optional[int] = None
        self.fft_size: Optional[int] = None

    def __call__(
        self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState, parts: int = 1
    ) -> float:
        if self.fft_size is None or self.fragment_length is None:
            raise ValueError("Fragment length and FFT size must be set before calling the loss function.")

        spectral_loss = self.spectral_loss(audio, approximation, state, parts=parts)
        temporal_loss = root_mean_squared_error(audio, approximation)

        return self.combine_losses(spectral_loss, temporal_loss)

    def set_fragment_length(self, length: int) -> None:
        min_fft_size = self.config.min_fft_size
        self.fragment_length = length
        self.fft_size = max(min_fft_size, 1 << (length - 1).bit_length())

    def spectral_loss(
        self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState, parts: int = 1
    ) -> float:
        fragment_padded = self.pad(audio, state.fragments, state.fragment_id, parts)
        approx_padded = self.pad(approximation, state.approximations[self.generator_name], state.fragment_id, parts)

        window = get_window("hann", len(fragment_padded))
        fragment_windowed = fragment_padded * window
        approx_windowed = approx_padded * window

        frag_spectrum = np.abs(scipy.fft.rfft(fragment_windowed))
        approx_spectrum = np.abs(scipy.fft.rfft(approx_windowed))

        freqs = scipy.fft.rfftfreq(len(fragment_windowed), 1 / self.config.sample_rate)
        audible_mask = (freqs >= MIN_FREQUENCY) & (freqs <= MAX_FREQUENCY)

        audible_freqs = freqs[audible_mask]
        frag_audible = frag_spectrum[audible_mask]
        approx_audible = approx_spectrum[audible_mask]

        density_weights = 1.0 / np.maximum(audible_freqs, MIN_FREQUENCY)
        perceptual_weights = self._a_weighting(audible_freqs)
        weights = density_weights * perceptual_weights

        frag_log = np.log1p(frag_audible)
        approx_log = np.log1p(approx_audible)
        squared_errors = (frag_log - approx_log) ** 2

        return np.average(squared_errors, weights=weights)

    def pad(
        self, audio: np.ndarray, data: Union[np.ndarray, List[np.ndarray]], fragment_id: int, parts: int = 1
    ) -> np.ndarray:
        current_length = len(audio)
        assert (
            current_length == self.fragment_length * parts
        ), f"Audio length {current_length} does not match expected {self.fragment_length * parts}"

        padding_needed = max(0, self.fft_size - current_length)

        if padding_needed == 0:
            return audio

        frames_needed = int(np.ceil(padding_needed / self.fragment_length))
        paddings = []
        total_padding_length = 0

        for idx in range(frames_needed, 0, -1):
            if total_padding_length >= padding_needed:
                break

            prev_fragment_id = fragment_id - idx

            if 0 <= prev_fragment_id < len(data):
                frame = data[prev_fragment_id]
            else:
                frame = np.zeros(self.fragment_length, dtype=audio.dtype)

            remaining_needed = padding_needed - total_padding_length
            frame_to_use = frame[: min(len(frame), remaining_needed)]

            paddings.append(frame_to_use)
            total_padding_length += len(frame_to_use)

        if paddings:
            return np.concatenate(paddings + [audio])
        else:
            return audio

    def _a_weighting(self, freqs: np.ndarray) -> np.ndarray:
        freqs = np.maximum(freqs, 1e-6)
        f_sq = freqs**2
        numerator = 12194**2 * f_sq**2
        denominator = (f_sq + 20.6**2) * np.sqrt((f_sq + 107.7**2) * (f_sq + 737.9**2)) * (f_sq + 12194**2)

        a_weight = numerator / denominator
        return a_weight / np.max(a_weight)

    def combine_losses(self, spectral_loss: float, temporal_loss: float) -> float:
        # print(f"Spectral Loss: {spectral_loss}, Temporal Loss: {temporal_loss}")
        alpha = self.config.loss_alpha
        return alpha * spectral_loss + (1 - alpha) * temporal_loss
