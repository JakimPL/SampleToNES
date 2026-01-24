from sampletones.constants.enums import InstructionClassName

from .maps import INSTRUCTION_CLASS_MAP
from .types import InstructionTypeUnion


def get_instruction_by_type(instruction_class_map: InstructionClassName) -> InstructionTypeUnion:
    return INSTRUCTION_CLASS_MAP[instruction_class_map]
