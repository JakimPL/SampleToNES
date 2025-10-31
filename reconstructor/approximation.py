from pydantic import BaseModel

from library.fragment import Fragment
from typehints.enums import GeneratorName
from typehints.instructions import InstructionUnion


class ApproximationData(BaseModel):
    generator_name: GeneratorName
    approximation: Fragment
    instruction: InstructionUnion
    error: float

    class Config:
        arbitrary_types_allowed = True
