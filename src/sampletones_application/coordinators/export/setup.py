from typing import Protocol

from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import SampleExport


class ExportSetup(Protocol):
    """A setup dialog of the formats' own, opened where a save dialog would otherwise ask for the file.

    A format with choices of its own asks for them together with the destination, so the
    surfaces offering an export consult the formats' setups first and reach the save dialog for
    the formats that ask for a file alone. One setup may serve several formats, so each opening
    names the format the export is written in.
    """

    def open_project(self, export_format: ExportFormat) -> None: ...

    def open_sample(self, export_format: ExportFormat, request: SampleExport) -> None: ...
