from typing import Self, Tuple

from pydantic import BaseModel, Field, PositiveInt

from sampletones_core.calibration.paths import REFEREE_CONFIG_PATH
from sampletones_shared.utils.serialization import load_yaml_model


class RefereeConfig(BaseModel, frozen=True):
    """
    Tuning of the built-in multi-resolution auditory referee.

    Values are loaded from the packaged `calibration/referee.yaml`, so referee
    scores stay comparable across calibration runs while remaining adjustable
    in one place.
    """

    window_sizes: Tuple[PositiveInt, ...] = Field(
        min_length=1,
        description="STFT window sizes covering the time-frequency trade-off.",
    )
    hop_divisor: PositiveInt = Field(description="Window size divided by this gives the STFT hop.")
    band_count: PositiveInt = Field(description="Number of ERB-spaced aggregation bands.")
    low_frequency: float = Field(gt=0.0, description="Lower bound of the band axis in Hz.")
    energy_floor: float = Field(gt=0.0, description="Absolute floor keeping silent band energies finite.")
    audibility_range_decibels: float = Field(
        gt=0.0,
        description="Audible range below the reference's loudest band; quieter content saturates.",
    )

    @classmethod
    def load(cls) -> Self:
        """
        Load the packaged referee tuning.

        Returns:
            The referee configuration validated from `sampletones_config/calibration/referee.yaml`.

        Raises:
            TypeError: If the configuration file holds anything other than a mapping.
        """
        return load_yaml_model(REFEREE_CONFIG_PATH, cls)
