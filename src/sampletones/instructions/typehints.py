from typing import Literal, Type, TypeVar, Union

from .instruction import Instruction
from .noise import NoiseInstruction
from .pulse import PulseInstruction
from .triangle import TriangleInstruction

InstructionT = TypeVar("InstructionT", bound=Instruction)
InstructionClass = Type[InstructionT]
InstructionUnion = Union[PulseInstruction, TriangleInstruction, NoiseInstruction]
InstructionTypeUnion = Union[Type[PulseInstruction], Type[TriangleInstruction], Type[NoiseInstruction]]

InstructionFields = Literal["on", "volume", "pitch", "duty_cycle", "period", "short"]
