from pathlib import Path
from typing import Protocol

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.request import ProjectExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_player.export.program import NSFProgram


class NSFExportServiceProtocol(Protocol):
    """The slice of the export service an NSF export hands its run to.

    Typing the collaborator structurally keeps the logic layer independent of the service
    implementation; the composition root supplies the real service.
    """

    def export_sample(
        self,
        destination: Path,
        backend: ExportBackend,
        request: SampleExport,
    ) -> None: ...

    def export_project(
        self,
        destination: Path,
        backend: ExportBackend,
        request: ProjectExport,
    ) -> None: ...


class NSFProgramBackend(Protocol):
    """The backend writing console programs, which binds a run to the program a setup chose."""

    def choosing(self, program: NSFProgram) -> ExportBackend: ...

    def extension(self, scope: ExportScope) -> str: ...
