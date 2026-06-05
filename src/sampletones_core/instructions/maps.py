from typing import Dict, Final

from sampletones_core.constants.enums import InstructionClassName

from .noise import NoiseInstruction
from .pulse import PulseInstruction
from .triangle import TriangleInstruction
from .types import InstructionTypeUnion

INSTRUCTION_CLASS_MAP: Final[Dict[InstructionClassName, InstructionTypeUnion]] = {
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}
