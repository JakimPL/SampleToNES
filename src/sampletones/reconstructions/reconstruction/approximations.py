from types import ModuleType

import numpy as np
from pydantic import ConfigDict, Field, field_serializer

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel
from sampletones.typehints import SerializedData
from sampletones.utils import serialize_array


class ApproximationsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    approximation: np.ndarray = Field(..., description="Audio approximation for the generator")

    @field_serializer("approximation")
    def serialize_approximation(self, approximation: np.ndarray) -> SerializedData:
        return serialize_array(approximation)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.reconstruction import FBApproximationsItem

        return FBApproximationsItem

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.reconstruction import FBApproximationsItem

        return FBApproximationsItem.FBApproximationsItem
