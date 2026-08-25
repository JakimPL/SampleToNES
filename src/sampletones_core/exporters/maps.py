from typing import Dict, Type

from sampletones_core.constants.enums import ChannelName
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

CHANNEL_TO_EXPORTER_MAP: Dict[ChannelName, ExporterTypeUnion] = {
    ChannelName.PULSE1: PulseExporter,
    ChannelName.PULSE2: PulseExporter,
    ChannelName.TRIANGLE: TriangleExporter,
    ChannelName.NOISE: NoiseExporter,
}
