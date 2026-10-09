from pathlib import Path
from typing import Protocol

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import InstrumentExport


class InstrumentExportServiceProtocol(Protocol):
    """The slice of the export service one instrument's export drives.

    Typing the collaborator structurally keeps the logic layer independent of the service
    implementation; the composition root supplies the real service.
    """

    def export_instrument(
        self,
        destination: Path,
        backend: ExportBackend,
        request: InstrumentExport,
    ) -> None: ...
