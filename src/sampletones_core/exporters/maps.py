from typing import Dict, Type

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.instructions import (
    Instruction,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)

from .implementation.noise import NoiseExporter
from .implementation.pulse import PulseExporter
from .implementation.triangle import TriangleExporter
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
