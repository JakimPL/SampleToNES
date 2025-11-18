from sampletones.constants.enums import InstructionClassName

from .maps import INSTRUCTION_CLASS_MAP


def get_instruction_by_type(instruction_class_map: InstructionClassName):
    return INSTRUCTION_CLASS_MAP[instruction_class_map]
