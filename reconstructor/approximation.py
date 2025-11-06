from pydantic import BaseModel

from constants.enums import GeneratorName
from library.fragment import Fragment
from typehints.instructions import InstructionUnion


class ApproximationData(BaseModel):
    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float

    class Config:
        arbitrary_types_allowed = True
