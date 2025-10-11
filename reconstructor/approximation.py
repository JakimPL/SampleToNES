from typing import Any, Optional, Tuple

from pydantic import BaseModel

from instructions.instruction import Instruction
from reconstructor.fragment import Fragment


class FragmentApproximation(BaseModel):
    generator_name: str
    fragment: Fragment
    instruction: Instruction
    initials: Optional[Tuple[Any, ...]]
    terminals: Optional[Tuple[Any, ...]]
    error: float

    class Config:
        arbitrary_types_allowed = True
