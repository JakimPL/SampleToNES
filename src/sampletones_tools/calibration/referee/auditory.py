from typing import Final, List

import numpy as np

from sampletones_tools.calibration.config.referee import RefereeConfig

from .bands import BandAnalyzer
from .protocol import Judgment

AUDITORY_REFEREE_NAME: Final[str] = "mr-auditory-dB"


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

    Every band weighs the same whatever it holds, so the score reads timbre and the balance of
    tone against noise across the whole spectrum. On a lone tone the empty bands outnumber the
    occupied ones, and a render adding content to them reads as farther than silence.
    """

    def __init__(self, sample_rate: int, *, config: RefereeConfig) -> None:
        self.sample_rate = sample_rate
        self.config = config
        self.analyzer = BandAnalyzer(sample_rate, config=config)

    @property
    def name(self) -> str:
        return AUDITORY_REFEREE_NAME

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        """
        Mean absolute log-spectral deviation between two equal-length signals.

        Args:
            reference: Reference waveform.
            estimate: Waveform under evaluation, of the same length.

        Returns:
            Judgment: The mean absolute deviation in dB over bands, frames, and resolutions.

        Raises:
            ValueError: If the signals differ in length.
        """
        if reference.shape != estimate.shape:
            raise ValueError(f"signal shapes differ: {reference.shape} vs {estimate.shape}")

        distances: List[float] = []
        for window_size in self.analyzer.window_sizes:
            reference_energy = self.analyzer.band_energies(reference, window_size)
            estimate_energy = self.analyzer.band_energies(estimate, window_size)
            floor = self.analyzer.audibility_floor(
                reference_energy,
                range_decibels=self.config.audibility_range_decibels,
            )
            reference_bands = 10.0 * np.log10(reference_energy + floor)
            estimate_bands = 10.0 * np.log10(estimate_energy + floor)
            distances.append(float(np.mean(np.abs(reference_bands - estimate_bands))))

        return Judgment(score=float(np.mean(distances)), components={})
