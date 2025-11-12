from typing import Dict

from instructions import (
    InstructionClass,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter
from .typehints import ExporterClass

INSTRUCTION_TO_EXPORTER_MAP: Dict[InstructionClass, ExporterClass] = {
    TriangleInstruction: TriangleExporter,
    PulseInstruction: PulseExporter,
    NoiseInstruction: NoiseExporter,
}
