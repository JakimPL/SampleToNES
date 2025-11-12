from typing import Type, TypeVar, Union

from .instruction import Instruction
from .noise import NoiseInstruction
from .pulse import PulseInstruction
from .triangle import TriangleInstruction

InstructionType = TypeVar("InstructionType", bound=Instruction)
InstructionClass = Type[InstructionType]
InstructionUnion = Union[PulseInstruction, TriangleInstruction, NoiseInstruction]
