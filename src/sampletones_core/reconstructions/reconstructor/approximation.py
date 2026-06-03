from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Fragment
from sampletones_core.instructions import InstructionUnion


class ApproximationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
