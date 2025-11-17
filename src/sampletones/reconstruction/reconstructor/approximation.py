from pydantic import BaseModel, ConfigDict

from sampletones.constants.enums import GeneratorName
from sampletones.ffts import Fragment
from sampletones.instructions import InstructionUnion


class ApproximationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float
