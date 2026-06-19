import numpy as np
from pydantic import ConfigDict, Field, field_serializer

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import DataModel
from sampletones_shared.types.data import SerializedData
from sampletones_shared.utils.serialization import serialize_array


class ApproximationsItem(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    approximation: np.ndarray = Field(..., description="Audio approximation for the generator")

    @field_serializer("approximation")
    def serialize_approximation(self, approximation: np.ndarray) -> SerializedData:
        return serialize_array(approximation)
