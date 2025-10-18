from pydantic import BaseModel

from library.fragment import Fragment
from typehints.general import Initials
from typehints.instructions import InstructionUnion


class FragmentApproximation(BaseModel):
    generator_name: str
    fragment: Fragment
    instruction: InstructionUnion
    initials: Initials
    terminals: Initials
    error: float

    class Config:
        arbitrary_types_allowed = True
