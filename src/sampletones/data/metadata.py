from __future__ import annotations

from typing import Self, Type

from pydantic import ConfigDict, Field

from sampletones.constants.application import (
    SAMPLETONES_LIBRARY_DATA_VERSION,
    SAMPLETONES_NAME,
    SAMPLETONES_RECONSTRUCTION_DATA_VERSION,
    SAMPLETONES_VERSION,
)

from .model import DataModel
from .scheme import FlatBufferBuilderProtocol, FlatBufferReaderProtocol


class Metadata(DataModel):
    model_config = ConfigDict(frozen=True)

    application_name: str = Field(default=SAMPLETONES_NAME)
    version: str = Field(default=SAMPLETONES_VERSION)
    library_data_version: str = Field(default=SAMPLETONES_LIBRARY_DATA_VERSION)
    reconstruction_data_version: str = Field(default=SAMPLETONES_RECONSTRUCTION_DATA_VERSION)

    @classmethod
    def default(cls) -> Self:
        return cls()

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.metadata import FBMetadata

        return FBMetadata

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.metadata import FBMetadata

        return FBMetadata.FBMetadata
