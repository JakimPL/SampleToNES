from typing import Dict

from exporters.noise import NoiseExporter
from exporters.pulse import PulseExporter
from exporters.triangle import TriangleExporter
from exporters.typehints import ExporterClass
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from instructions.typehints import InstructionClass

INSTRUCTION_TO_EXPORTER_MAP: Dict[InstructionClass, ExporterClass] = {
    TriangleInstruction: TriangleExporter,
    PulseInstruction: PulseExporter,
    NoiseInstruction: NoiseExporter,
}
