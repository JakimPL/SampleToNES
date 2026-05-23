from typing import Type

import numpy as np
from pydantic import ConfigDict, Field, field_serializer

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel, FlatBufferBuilderProtocol, FlatBufferReaderProtocol
from sampletones_shared.types.data import SerializedData
from sampletones_shared.utils.serialization import serialize_array


class ApproximationsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    approximation: np.ndarray = Field(..., description="Audio approximation for the generator")

    @field_serializer("approximation")
    def serialize_approximation(self, approximation: np.ndarray) -> SerializedData:
        return serialize_array(approximation)

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.reconstruction import FBApproximationsItem

        return FBApproximationsItem

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.reconstruction import FBApproximationsItem

        return FBApproximationsItem.FBApproximationsItem
