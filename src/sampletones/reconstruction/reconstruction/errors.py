from types import ModuleType

import numpy as np
from pydantic import ConfigDict, Field, field_serializer

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel
from sampletones.typehints import SerializedData
from sampletones.utils import serialize_array


class Errors(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    errors: np.ndarray = Field(..., description="Reconstruction errors for the generator")
    total_error: float = Field(..., description="Total reconstruction error for the generator")

    @field_serializer("errors")
    def serialize_errors(self, errors: np.ndarray) -> SerializedData:
        return serialize_array(errors)

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.reconstruction import FBErrors

        return FBErrors

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.reconstruction import FBErrors

        return FBErrors.FBErrors
