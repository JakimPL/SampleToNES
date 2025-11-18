from typing import Dict

from sampletones.constants.enums import InstructionClassName

from .noise import NoiseInstruction
from .pulse import PulseInstruction
from .triangle import TriangleInstruction
from .typehints import InstructionClass

INSTRUCTION_CLASS_MAP: Dict[InstructionClassName, InstructionClass] = {
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}
