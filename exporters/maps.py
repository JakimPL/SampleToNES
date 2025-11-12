from typing import Dict

from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from instructions.typehints import InstructionClass

from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter
from .typehints import ExporterClass

INSTRUCTION_TO_EXPORTER_MAP: Dict[InstructionClass, ExporterClass] = {
    TriangleInstruction: TriangleExporter,
    PulseInstruction: PulseExporter,
    NoiseInstruction: NoiseExporter,
}
