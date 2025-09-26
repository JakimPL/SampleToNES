from typing import List, Optional, Union

import numpy as np
import scipy.fft
from scipy.signal import get_window
from sklearn.metrics import root_mean_squared_error

from config import Config
from constants import MAX_FREQUENCY, MIN_FREQUENCY
from reconstructor.state import ReconstructionState


class Loss:
    def __init__(self, config: Config, alpha: float = 0.8, min_fft_size: int = 2048):
        self.config = config
        self.alpha = alpha
        self.fragment_length: Optional[int] = None
        self.fft_size: Optional[int] = None
        self.min_fft_size = min_fft_size

    def __call__(self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState) -> float:
        if self.fft_size is None or self.fragment_length is None:
            raise ValueError("Fragment length and FFT size must be set before calling the loss function.")

        spectral_loss = self.spectral_loss(audio, approximation, state)
        temporal_loss = root_mean_squared_error(audio, approximation)

        return self.combine_losses(spectral_loss, temporal_loss)

    def set_fragment_length(self, length: int) -> None:
        self.fragment_length = length
        self.fft_size = max(self.min_fft_size, 1 << (length - 1).bit_length())

    def spectral_loss(self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState) -> float:
        fragment_padded = self.pad(audio, state.fragments, state.fragment_id)
        approx_padded = self.pad(approximation, state.approximations, state.fragment_id)

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

    def pad(self, audio: np.ndarray, data: Union[np.ndarray, List[np.ndarray]], fragment_id: int) -> np.ndarray:
        assert len(audio) == self.fragment_length
        paddings = []
        if self.fragment_length < self.fft_size:
            items = int(np.ceil(self.fft_size / self.fragment_length))
            total_length = 0
            for idx in range(items - 1, 0, -1):
                pad_width = min(self.fft_size - total_length, self.fragment_length)
                total_length += pad_width
                if 0 <= fragment_id - idx < len(data):
                    paddings.append(data[fragment_id - idx])
                else:
                    paddings.append(np.pad(audio, (pad_width, 0), mode="constant"))

            paddings.append(audio)
            return np.concatenate(paddings)

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
        return self.alpha * spectral_loss + (1 - self.alpha) * temporal_loss
