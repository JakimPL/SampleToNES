from typing import Type, TypeVar

from .exporter import Exporter

ExporterT = TypeVar("ExporterT", bound=Exporter)
ExporterClass = Type[ExporterT]
