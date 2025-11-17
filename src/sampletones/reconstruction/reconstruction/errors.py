from types import ModuleType

import numpy as np
from pydantic import ConfigDict, Field

from sampletones.constants.enums import GeneratorName
from sampletones.data import DataModel


class Errors(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName = Field(..., description="Name of the generator")
    errors: np.ndarray = Field(..., description="Reconstruction errors for the generator")
    total_error: float = Field(..., description="Total reconstruction error for the generator")

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        import schemas.reconstruction.FBErrors as FBErrors

        return FBErrors

    @classmethod
    def buffer_reader(cls) -> type:
        import schemas.reconstruction.FBErrors as FBErrors

        return FBErrors.FBErrors
