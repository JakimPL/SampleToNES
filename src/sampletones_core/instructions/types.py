from typing import Literal, Type, TypeVar, Union

from .implementation.noise import NoiseInstruction
from .implementation.pulse import PulseInstruction
from .implementation.triangle import TriangleInstruction
from .instruction import Instruction

InstructionT = TypeVar("InstructionT", bound=Instruction)
InstructionClass = Type[InstructionT]
InstructionUnion = Union[PulseInstruction, TriangleInstruction, NoiseInstruction]
InstructionTypeUnion = Union[Type[PulseInstruction], Type[TriangleInstruction], Type[NoiseInstruction]]

InstructionFields = Literal["on", "volume", "pitch", "duty_cycle", "period", "short"]
