from typing import Protocol

from sampletones_core.exports.request import SampleExport


class ExportSetup(Protocol):
    """A format's own setup dialog, opened where a save dialog would otherwise ask for the file.

    A format with choices of its own asks for them together with the destination, so the
    surfaces offering an export consult the formats' setups first and reach the save dialog for
    the formats that ask for a file alone.
    """

    def open_project(self) -> None: ...

    def open_sample(self, request: SampleExport) -> None: ...
