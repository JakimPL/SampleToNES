from pydantic import BaseModel, ConfigDict, Field

from constants.general import (
    LIBRARY_DIRECTORY,
    MAX_PITCH,
    MAX_WORKERS,
    MIN_PITCH,
    NORMALIZE,
    OUTPUT_DIRECTORY,
    QUANTIZE,
)


class GeneralConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    library_directory: str = Field(default=LIBRARY_DIRECTORY)
    output_directory: str = Field(default=OUTPUT_DIRECTORY)
