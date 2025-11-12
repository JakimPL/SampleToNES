from pydantic import BaseModel, ConfigDict

from sampletones.constants import GeneratorName
from sampletones.instructions import InstructionUnion
from sampletones.library import Fragment


class ApproximationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float
