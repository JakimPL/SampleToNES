from pydantic import BaseModel, ConfigDict

from constants import GeneratorName
from instructions import InstructionUnion
from library import Fragment


class ApproximationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float
