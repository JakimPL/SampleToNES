from pathlib import Path
from typing import Final, Tuple

from pydantic import BaseModel, Field, PositiveInt

import sampletones_config
from sampletones_shared.utils.serialization import load_yaml

CALIBRATION_CONFIG_DIRECTORY: Final[Path] = Path(sampletones_config.__file__).parent / "calibration"
REFEREE_CONFIG_PATH: Final[Path] = CALIBRATION_CONFIG_DIRECTORY / "referee.yaml"


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


def load_referee_config() -> RefereeConfig:
    """
    Load the packaged referee tuning.

    Returns:
        The referee configuration validated from `sampletones_config/calibration/referee.yaml`.

    Raises:
        TypeError: If the configuration file holds anything other than a mapping.
    """
    raw = load_yaml(REFEREE_CONFIG_PATH)
    if not isinstance(raw, dict):
        raise TypeError(f"Referee configuration {REFEREE_CONFIG_PATH} must contain a mapping, got {type(raw)}")

    return RefereeConfig.model_validate(raw)
