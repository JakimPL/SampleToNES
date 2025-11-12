from pydantic import BaseModel, ConfigDict

from constants.enums import GeneratorName
from instructions.typehints import InstructionUnion
from library.fragment import Fragment


class ApproximationData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float
