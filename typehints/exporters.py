from typing import Type, TypeVar

from exporters.exporter import Exporter

ExporterType = TypeVar("ExporterType", bound="Exporter")
ExporterClass = Type[ExporterType]
