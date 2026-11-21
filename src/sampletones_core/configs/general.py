from typing import Self

from pydantic import AliasChoices, ConfigDict, Field, model_validator

from sampletones_core.constants.algorithm import (
    COEFFICIENT_AUDIBILITY_FLOOR,
    COEFFICIENT_PERCENTILE,
    LEVEL_METHOD,
    MAX_WORKERS,
    NORMALIZE,
    QUANTIZATION_LEVELS,
    QUANTIZE,
)
from sampletones_core.constants.enums import LevelMethod
from sampletones_core.constants.general import MAX_PITCH, MIN_PITCH, PlayedPitch
from sampletones_core.data import DataModel
from sampletones_shared.paths.user import LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY

from .pitch import PitchRange


class GeneralConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: PlayedPitch = Field(default=MIN_PITCH)
    max_pitch: PlayedPitch = Field(default=MAX_PITCH)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    quantization_levels: int = Field(default=QUANTIZATION_LEVELS, ge=3)
    level: LevelMethod = Field(default=LEVEL_METHOD)
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

    @model_validator(mode="after")
    def _check_pitch_range(self) -> Self:
        PitchRange(min_pitch=self.min_pitch, max_pitch=self.max_pitch)
        return self

    @property
    def pitch_range(self) -> PitchRange:
        return PitchRange(min_pitch=self.min_pitch, max_pitch=self.max_pitch)
