from typing import Dict, Type

from sampletones.constants.enums import GeneratorName
from sampletones.instructions import (
    Instruction,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter
from .types import ExporterTypeUnion

INSTRUCTION_TO_EXPORTER_MAP: Dict[Type[Instruction], ExporterTypeUnion] = {
    PulseInstruction: PulseExporter,
    TriangleInstruction: TriangleExporter,
    NoiseInstruction: NoiseExporter,
}

GENERATOR_NAME_TO_EXPORTER_MAP: Dict[GeneratorName, ExporterTypeUnion] = {
    GeneratorName.PULSE1: PulseExporter,
    GeneratorName.PULSE2: PulseExporter,
    GeneratorName.TRIANGLE: TriangleExporter,
    GeneratorName.NOISE: NoiseExporter,
}
