from typing import Type, TypeVar, Union

from instructions.instruction import Instruction
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction

InstructionType = TypeVar("InstructionType", bound=Instruction)
InstructionClass = Type[InstructionType]
InstructionUnion = Union[PulseInstruction, TriangleInstruction, NoiseInstruction]
