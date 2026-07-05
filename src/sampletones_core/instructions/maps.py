from typing import Dict, Final

from sampletones_core.constants.enums import InstructionClassName

from .implementation.noise import NoiseInstruction
from .implementation.pulse import PulseInstruction
from .implementation.triangle import TriangleInstruction
from .types import InstructionTypeUnion

INSTRUCTION_CLASS_MAP: Final[Dict[InstructionClassName, InstructionTypeUnion]] = {
    InstructionClassName.PULSE_INSTRUCTION: PulseInstruction,
    InstructionClassName.TRIANGLE_INSTRUCTION: TriangleInstruction,
    InstructionClassName.NOISE_INSTRUCTION: NoiseInstruction,
}
