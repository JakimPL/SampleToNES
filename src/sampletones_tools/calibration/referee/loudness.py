from dataclasses import dataclass
from typing import Final, List

import numpy as np

from sampletones_tools.calibration.config.referee import RefereeConfig

from .bands import BandAnalyzer
from .level import level_difference_decibels, matched_to_reference
from .protocol import Judgment

LOUDNESS_REFEREE_NAME: Final[str] = "mr-loudness-dB"
MISSING_COMPONENT: Final[str] = "missing"
ADDED_COMPONENT: Final[str] = "added"
LEVEL_COMPONENT: Final[str] = "level"


@dataclass(frozen=True)
class Deviation:
    """The loudness-weighted log-spectral deviation of one resolution, split by which side is louder.

    Attributes:
        missing: The part where the reference is louder: content the estimate lacks.
        added: The part where the estimate is louder: content the estimate brings in.
    """

    missing: float
    added: float


class LoudnessWeightedReferee:
    """
    Log-spectral distance over ERB-spaced bands, weighted by how loud each band plays.

    Each band-frame's absolute deviation in decibels counts in proportion to the specific
    loudness of the louder side, the energy relative to the reference's loudest band raised to
    the compression exponent. Occupied bands carry the score and empty ones nearly vanish, so a
    missing tone costs what it is heard as, and an estimate's energy measured against the
    reference's maximum weighs above one where it brings in louder content. The estimate is
    brought to the reference's level first, so the score reads shape and balance, and the level
    difference is reported beside it. The deviation splits into ``missing`` (a dull estimate)
    and ``added`` (a buzzy one), which sum to the score. Lower scores mean closer
    reconstructions; identical signals score zero.
    """

    def __init__(self, sample_rate: int, *, config: RefereeConfig) -> None:
        self.sample_rate = sample_rate
        self.config = config
        self.analyzer = BandAnalyzer(sample_rate, config=config)

    @property
    def name(self) -> str:
        return LOUDNESS_REFEREE_NAME

    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        """
        Loudness-weighted log-spectral deviation between two equal-length signals.

        Args:
            reference: Reference waveform.
            estimate: Waveform under evaluation, of the same length.

        Returns:
            Judgment: The mean weighted deviation in dB over resolutions, with its missing and added
                parts and the level difference in dB.

        Raises:
            ValueError: If the signals differ in length.
        """
        if reference.shape != estimate.shape:
            raise ValueError(f"signal shapes differ: {reference.shape} vs {estimate.shape}")

        level = level_difference_decibels(
            reference,
            estimate,
            self.sample_rate,
            energy_floor=self.config.energy_floor,
            range_decibels=self.config.dynamic_range_decibels,
        )
        compared = matched_to_reference(estimate, level_decibels=level) if self.config.level_matching else estimate
        deviations: List[Deviation] = [
            self._deviation(reference, compared, window_size) for window_size in self.analyzer.window_sizes
        ]
        missing = float(np.mean([deviation.missing for deviation in deviations]))
        added = float(np.mean([deviation.added for deviation in deviations]))
        return Judgment(
            score=missing + added,
            components={
                MISSING_COMPONENT: missing,
                ADDED_COMPONENT: added,
                LEVEL_COMPONENT: level,
            },
        )

    def _deviation(
        self,
        reference: np.ndarray,
        estimate: np.ndarray,
        window_size: int,
    ) -> Deviation:
        reference_energy = self.analyzer.band_energies(reference, window_size)
        estimate_energy = self.analyzer.band_energies(estimate, window_size)
        loudest = max(float(np.max(reference_energy)), self.config.energy_floor)
        floor = self.analyzer.audibility_floor(
            reference_energy,
            range_decibels=self.config.dynamic_range_decibels,
        )
        deviation = 10.0 * np.log10((reference_energy + floor) / (estimate_energy + floor))
        weights = np.maximum(reference_energy, estimate_energy) / loudest
        weights = weights**self.config.compression_exponent
        total = float(np.sum(weights))
        if total == 0.0:
            return Deviation(missing=0.0, added=0.0)

        return Deviation(
            missing=float(np.sum(weights * np.maximum(deviation, 0.0))) / total,
            added=float(np.sum(weights * np.maximum(-deviation, 0.0))) / total,
        )
