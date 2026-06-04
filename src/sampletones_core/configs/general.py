from typing import Type

from pydantic import ConfigDict, Field

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_WORKERS,
    MIN_PITCH,
    NORMALIZE,
    QUANTIZE,
)
from sampletones_core.data import (
    DataModel,
    FlatBufferBuilderProtocol,
    FlatBufferReaderProtocol,
)
from sampletones_core.paths import LIBRARY_DIRECTORY, OUTPUT_DIRECTORY


class GeneralConfig(DataModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_pitch: int = Field(default=MIN_PITCH, ge=1, le=127)
    max_pitch: int = Field(default=MAX_PITCH, ge=1, le=127)
    normalize: bool = Field(default=NORMALIZE)
    quantize: bool = Field(default=QUANTIZE)
    max_workers: int = Field(default=MAX_WORKERS, ge=1)

    library_directory: str = Field(default=str(LIBRARY_DIRECTORY))
    output_directory: str = Field(default=str(OUTPUT_DIRECTORY))

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.configs import FBGeneralConfig

        return FBGeneralConfig

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.configs import FBGeneralConfig

        return FBGeneralConfig.FBGeneralConfig
