from typing import List, Optional, Union

import numpy as np
import scipy.fft
from scipy.signal import get_window
from sklearn.metrics import root_mean_squared_error

from config import Config
from constants import MAX_FREQUENCY, MIN_FREQUENCY
from reconstructor.state import ReconstructionState


class Loss:
    def __init__(self, config: Config, alpha: float = 0.5):
        self.config = config
        self.alpha = alpha
        self.fragment_length: Optional[int] = None
        self.fft_size: Optional[int] = None

    def __call__(self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState) -> float:
        if self.fft_size is None or self.fragment_length is None:
            raise ValueError("Fragment length and FFT size must be set before calling the loss function.")

        spectral_loss = self.spectral_loss(audio, approximation, state)
        temporal_loss = root_mean_squared_error(audio, approximation)

        return self.alpha * spectral_loss + (1 - self.alpha) * temporal_loss

    def set_fragment_length(self, length: int) -> None:
        self.fragment_length = length
        self.fft_size = 1 << (length - 1).bit_length()

    def spectral_loss(self, audio: np.ndarray, approximation: np.ndarray, state: ReconstructionState) -> float:
        fragment_padded = self.pad(audio, state.fragments, state.fragment_id)
        approx_padded = self.pad(approximation, state.approximations, state.fragment_id)

        window = get_window("hann", len(fragment_padded))
        fragment_windowed = fragment_padded * window
        approx_windowed = approx_padded * window

        frag_spectrum = np.abs(scipy.fft.fft(fragment_windowed))
        approx_spectrum = np.abs(scipy.fft.fft(approx_windowed))

        freqs = scipy.fft.fftfreq(len(fragment_windowed), 1 / self.config.sample_rate)
        audible_mask = (np.abs(freqs) >= MIN_FREQUENCY) & (np.abs(freqs) <= MAX_FREQUENCY)

        frag_log = np.log1p(frag_spectrum[audible_mask])
        approx_log = np.log1p(approx_spectrum[audible_mask])

        return np.mean((frag_log - approx_log) ** 2)

    def pad(self, audio: np.ndarray, data: Union[np.ndarray, List[np.ndarray]], fragment_id: int) -> np.ndarray:
        assert len(audio) == self.fragment_length
        if self.fragment_length < self.fft_size:
            pad_width = self.fft_size - self.fragment_length
            if fragment_id > 0:
                assert self.fragment_length == len(data[fragment_id - 1])
                return np.concatenate((data[fragment_id - 1][-pad_width:], audio))

            return np.pad(audio, (pad_width, 0), mode="constant")

        return audio
