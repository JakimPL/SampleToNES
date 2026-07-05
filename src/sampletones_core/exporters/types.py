from typing import Type, TypeVar, Union

from .implementation.noise import NoiseExporter
from .implementation.pulse import PulseExporter
from .implementation.triangle import TriangleExporter

ExporterT = TypeVar("ExporterT", PulseExporter, TriangleExporter, NoiseExporter)
ExporterClass = Type[ExporterT]
ExporterUnion = Union[PulseExporter, TriangleExporter, NoiseExporter]
ExporterTypeUnion = Union[Type[PulseExporter], Type[TriangleExporter], Type[NoiseExporter]]
