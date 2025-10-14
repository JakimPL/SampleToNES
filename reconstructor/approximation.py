from pydantic import BaseModel

from generators.types import Initials
from instructions.instruction import Instruction
from library.fragment import Fragment


class FragmentApproximation(BaseModel):
    generator_name: str
    fragment: Fragment
    instruction: Instruction
    initials: Initials
    terminals: Initials
    error: float

    class Config:
        arbitrary_types_allowed = True
