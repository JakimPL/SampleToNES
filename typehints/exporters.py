from typing import TypeVar

from exporters.exporter import Exporter

ExporterType = TypeVar("ExporterType", bound="Exporter")
