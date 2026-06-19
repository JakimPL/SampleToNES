from pydantic import AliasChoices, ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_WORKERS,
    MIN_PITCH,
    NORMALIZE,
    QUANTIZE,
)
from sampletones_core.data import DataModel
from sampletones_core.paths import LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY


class GeneralConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    library_directory: str = Field(default=str(LIBRARY_DIRECTORY))
    reconstructions_directory: str = Field(
        default=str(RECONSTRUCTIONS_DIRECTORY),
        validation_alias=AliasChoices(
            "output_directory",
            "reconstructions_directory",
        ),
    )
