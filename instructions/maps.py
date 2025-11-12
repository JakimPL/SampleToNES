from typing import Dict

from constants.enums import InstructionClassName
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from instructions.typehints import InstructionClass

INSTRUCTION_CLASS_MAP: Dict[InstructionClassName, InstructionClass] = {
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}
