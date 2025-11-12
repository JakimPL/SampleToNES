from typing import Type, TypeVar

from .exporter import Exporter

ExporterType = TypeVar("ExporterType", bound=Exporter)
ExporterClass = Type[ExporterType]
