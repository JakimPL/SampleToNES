from typing import Dict, Final, List

import numpy as np
from scipy.signal import stft

from sampletones_core.calibration.config.referee import RefereeConfig

ERB_RATE_SCALE: Final[float] = 21.4
ERB_RATE_FACTOR: Final[float] = 4.37e-3


class MultiResolutionAuditoryReferee:
    """
    Log-spectral distance over ERB-spaced bands at several STFT resolutions.

    Judges a reconstruction independently of the matching criterion: the configured
    window sizes cover the time-frequency trade-off the criterion resolves with a
    single frame, band energies aggregate on the ERB-rate axis with uniform band
    weights, and distances compare log magnitudes (mean absolute deviation in dB).
    Band energies are floored at the configured audibility range below the
    reference's loudest band, so the score reflects audible content, holds steady
    under a common gain, and saturates for bands one side leaves silent. Lower
    scores mean closer reconstructions; identical signals score zero.
    """

    def __init__(self, sample_rate: int, *, config: RefereeConfig) -> None:
        self.sample_rate = sample_rate
        self.config = config
        self._band_matrices: Dict[int, np.ndarray] = {
            window_size: self._band_matrix(sample_rate, window_size, config) for window_size in config.window_sizes
        }

    @property
    def name(self) -> str:
        return "mr-auditory-dB"

    def score(self, reference: np.ndarray, estimate: np.ndarray) -> float:
        """
        Mean absolute log-spectral deviation between two equal-length signals.

        Args:
            reference: Reference waveform.
            estimate: Waveform under evaluation, of the same length.

        Returns:
            Mean absolute deviation in dB over bands, frames, and resolutions.

        Raises:
            ValueError: If the signals differ in length.
        """
        if reference.shape != estimate.shape:
            raise ValueError(f"signal shapes differ: {reference.shape} vs {estimate.shape}")

        distances: List[float] = []
        for window_size, band_matrix in self._band_matrices.items():
            reference_energy = self._band_energy(reference, window_size, band_matrix)
            estimate_energy = self._band_energy(estimate, window_size, band_matrix)
            floor = max(float(np.max(reference_energy)), self.config.energy_floor) * 10.0 ** (
                -self.config.audibility_range_decibels / 10.0
            )
            reference_bands = 10.0 * np.log10(reference_energy + floor)
            estimate_bands = 10.0 * np.log10(estimate_energy + floor)
            distances.append(float(np.mean(np.abs(reference_bands - estimate_bands))))

        return float(np.mean(distances))

    def _band_energy(self, audio: np.ndarray, window_size: int, band_matrix: np.ndarray) -> np.ndarray:
        hop = window_size // self.config.hop_divisor
        _, _, spectrum = stft(
            audio.astype(np.float64),
            fs=self.sample_rate,
            nperseg=window_size,
            noverlap=window_size - hop,
        )
        energy = np.abs(spectrum) ** 2
        band_energy: np.ndarray = band_matrix @ energy
        return band_energy

    @classmethod
    def _band_matrix(cls, sample_rate: int, window_size: int, config: RefereeConfig) -> np.ndarray:
        """
        Rectangular aggregation matrix from STFT bins onto ERB-spaced bands.

        Band edges are uniform on the ERB-rate axis between the low-frequency bound and
        the Nyquist frequency; each STFT bin contributes its full energy to the band
        containing its center, and bins below the low-frequency bound join the first band.
        """
        frequencies = np.fft.rfftfreq(window_size, 1.0 / sample_rate)
        nyquist = sample_rate / 2.0
        edges_rate = np.linspace(
            cls._erb_rate(np.array([config.low_frequency]))[0],
            cls._erb_rate(np.array([nyquist]))[0],
            config.band_count + 1,
        )
        bin_rates = cls._erb_rate(frequencies)
        band_indices = np.clip(np.searchsorted(edges_rate, bin_rates, side="right") - 1, 0, config.band_count - 1)

        matrix = np.zeros((config.band_count, frequencies.shape[0]))
        matrix[band_indices, np.arange(frequencies.shape[0])] = 1.0
        return matrix

    @staticmethod
    def _erb_rate(frequencies: np.ndarray) -> np.ndarray:
        return ERB_RATE_SCALE * np.log10(1.0 + ERB_RATE_FACTOR * frequencies)
