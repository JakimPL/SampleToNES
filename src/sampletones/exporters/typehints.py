from typing import Type, TypeVar, Union

from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter

ExporterT = TypeVar("ExporterT", PulseExporter, TriangleExporter, NoiseExporter)
ExporterClass = Type[ExporterT]
ExporterUnion = Union[PulseExporter, TriangleExporter, NoiseExporter]
ExporterTypeUnion = Union[Type[PulseExporter], Type[TriangleExporter], Type[NoiseExporter]]
