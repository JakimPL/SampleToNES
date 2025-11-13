from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import (
    MAX_PITCH,
    MAX_WORKERS,
    MIN_PITCH,
    NORMALIZE,
    QUANTIZE,
)
from sampletones.constants.paths import LIBRARY_DIRECTORY, OUTPUT_DIRECTORY


class GeneralConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    library_directory: str = Field(default=str(LIBRARY_DIRECTORY))
    output_directory: str = Field(default=str(OUTPUT_DIRECTORY))
