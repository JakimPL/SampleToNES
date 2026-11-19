from typing import Dict, Tuple

import numpy as np
from scipy.signal import stft

from sampletones_core.audio.processing import decibels_to_power
from sampletones_core.fft.fft import calculate_fft_frequencies, erb_rate
from sampletones_tools.calibration.config.referee import RefereeConfig


class BandAnalyzer:
    """
    Band energies on the ERB-rate axis at every STFT resolution a referee reads.

    Each configured window size holds one rectangular aggregation matrix from STFT bins onto
    bands spaced uniformly in ERB rate, so referees built on the same configuration read the
    same time-frequency picture of a signal.
    """

    def __init__(self, sample_rate: int, *, config: RefereeConfig) -> None:
        self.sample_rate = sample_rate
        self.config = config
        self._band_matrices: Dict[int, np.ndarray] = {
            window_size: self._band_matrix(sample_rate, window_size, config) for window_size in config.window_sizes
        }

    @property
    def window_sizes(self) -> Tuple[int, ...]:
        return tuple(self._band_matrices)

    def band_energies(self, audio: np.ndarray, window_size: int) -> np.ndarray:
        """
        Energy per band and STFT frame of a signal at one resolution.

        Args:
            audio: The waveform to analyze.
            window_size: One of the configured window sizes; the hop is that size over the hop divisor.

        Returns:
            np.ndarray: Band energies, shaped (bands, frames).
        """
        hop = window_size // self.config.hop_divisor
        _, _, spectrum = stft(
            audio.astype(np.float64),
            fs=self.sample_rate,
            nperseg=window_size,
            noverlap=window_size - hop,
        )
        energy = np.abs(spectrum) ** 2
        band_energy: np.ndarray = self._band_matrices[window_size] @ energy
        return band_energy

    def audibility_floor(self, reference_energy: np.ndarray, *, range_decibels: float) -> float:
        """
        The energy ``range_decibels`` below the reference's loudest band.

        Content under this level counts as inaudible, so a band one side leaves silent saturates at
        the floor and a common gain on both signals leaves the ratio of floor to content unchanged.
        The configured energy floor keeps a silent reference's floor finite.
        """
        loudest = max(float(np.max(reference_energy)), self.config.energy_floor)
        return float(loudest * decibels_to_power(-range_decibels))

    @classmethod
    def _band_matrix(
        cls,
        sample_rate: int,
        window_size: int,
        config: RefereeConfig,
    ) -> np.ndarray:
        """
        Rectangular aggregation matrix from STFT bins onto ERB-spaced bands.

        Band edges are uniform on the ERB-rate axis between the low-frequency bound and
        the Nyquist frequency; each STFT bin contributes its full energy to the band
        containing its center, and bins below the low-frequency bound join the first band.
        """
        frequencies = calculate_fft_frequencies(window_size, sample_rate)
        nyquist = sample_rate / 2.0
        edges_rate = np.linspace(
            erb_rate(np.array([config.low_frequency]))[0],
            erb_rate(np.array([nyquist]))[0],
            config.band_count + 1,
        )
        bin_rates = erb_rate(frequencies)
        band_indices = np.clip(
            np.searchsorted(edges_rate, bin_rates, side="right") - 1,
            0,
            config.band_count - 1,
        )

        matrix = np.zeros((config.band_count, frequencies.shape[0]))
        matrix[band_indices, np.arange(frequencies.shape[0])] = 1.0
        return matrix
