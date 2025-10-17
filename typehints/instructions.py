from typing import TypeVar

from instructions.instruction import Instruction

InstructionType = TypeVar("InstructionType", bound="Instruction")
