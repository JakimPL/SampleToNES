from typing import Type, TypeVar, Union

from .exporter import Exporter
from .noise import NoiseExporter
from .pulse import PulseExporter
from .triangle import TriangleExporter

ExporterT = TypeVar("ExporterT", bound=Exporter)
ExporterClass = Type[ExporterT]
ExporterUnion = Union[PulseExporter, TriangleExporter, NoiseExporter]
