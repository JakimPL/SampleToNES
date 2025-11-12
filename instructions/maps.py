from typing import Dict

from constants import InstructionClassName

from .noise import NoiseInstruction
from .pulse import PulseInstruction
from .triangle import TriangleInstruction
from .typehints import InstructionClass

INSTRUCTION_CLASS_MAP: Dict[InstructionClassName, InstructionClass] = {
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}
