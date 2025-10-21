from pydantic import BaseModel

from library.fragment import Fragment
from typehints.instructions import InstructionUnion


class ApproximationData(BaseModel):
    generator_name: str
    approximation: Fragment
    instruction: InstructionUnion
    error: float

    class Config:
        arbitrary_types_allowed = True
