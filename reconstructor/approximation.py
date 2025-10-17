from typing import Generic

from pydantic import BaseModel

from library.fragment import Fragment
from typehints.general import Initials
from typehints.instructions import InstructionType


class FragmentApproximation(BaseModel, Generic[InstructionType]):
    generator_name: str
    fragment: Fragment
    instruction: InstructionType
    initials: Initials
    terminals: Initials
    error: float

    class Config:
        arbitrary_types_allowed = True
