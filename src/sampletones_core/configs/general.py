from pydantic import AliasChoices, ConfigDict, Field

from sampletones_core.constants.algorithm import (
    COEFFICIENT_AUDIBILITY_FLOOR,
    COEFFICIENT_PERCENTILE,
    MAX_WORKERS,
    NORMALIZE,
    QUANTIZATION_LEVELS,
    QUANTIZE,
)
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH
from sampletones_core.data import DataModel
from sampletones_shared.paths.user import LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY


class GeneralConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    quantization_levels: int = Field(default=QUANTIZATION_LEVELS, ge=3)
    coefficient_percentile: float = Field(default=COEFFICIENT_PERCENTILE, ge=0.0, le=100.0)
    coefficient_audibility_floor: float = Field(default=COEFFICIENT_AUDIBILITY_FLOOR, gt=0.0, le=1.0)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    library_directory: str = Field(default=str(LIBRARY_DIRECTORY))
    reconstructions_directory: str = Field(
        default=str(RECONSTRUCTIONS_DIRECTORY),
        validation_alias=AliasChoices(
            "output_directory",
            "reconstructions_directory",
        ),
    )
