from typing import Dict, Type

from sampletones.instructions import (
    Instruction,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter
from .typehints import ExporterTypeUnion

INSTRUCTION_TO_EXPORTER_MAP: Dict[Type[Instruction], ExporterTypeUnion] = {
    TriangleInstruction: TriangleExporter,
    PulseInstruction: PulseExporter,
    NoiseInstruction: NoiseExporter,
}
