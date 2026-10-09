from typing import Self, Tuple

from pydantic import BaseModel, Field, PositiveInt

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import REFEREE_CONFIG_PATH


class RefereeConfig(BaseModel, frozen=True):
    """
    Tuning of the built-in referees, which share one band analysis.

    Values are loaded from the packaged `calibration/referee.yaml`, so referee
    scores stay comparable across calibration runs while remaining adjustable
    in one place.
    """

    window_sizes: Tuple[PositiveInt, ...] = Field(
        min_length=1,
        description="STFT window sizes covering the time-frequency trade-off.",
    )
    hop_divisor: PositiveInt = Field(
        description="Window size divided by this gives the STFT hop.",
    )
    band_count: PositiveInt = Field(
        description="Number of ERB-spaced aggregation bands.",
    )
    low_frequency: float = Field(
        gt=0.0,
        description="Lower bound of the band axis in Hz.",
    )
    energy_floor: float = Field(
        gt=0.0,
        description="Absolute floor keeping silent band energies finite.",
    )
    audibility_range_decibels: float = Field(
        gt=0.0,
        description="Audible range below the reference's loudest band; quieter content saturates.",
    )
    compression_exponent: float = Field(
        gt=0.0,
        le=1.0,
        description="Exponent turning a band's energy relative to the loudest into its specific loudness.",
    )
    dynamic_range_decibels: float = Field(
        gt=0.0,
        description="Range below the reference's loudest band the loudness-weighted referee reads.",
    )
    level_matching: bool = Field(
        description="Whether the loudness-weighted referee matches the estimate's level before comparing shapes.",
    )

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged referee tuning.

        Returns:
            The referee configuration validated from `sampletones_tools/calibration/config/referee.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(REFEREE_CONFIG_PATH, cls)
