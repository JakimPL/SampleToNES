from pathlib import Path
from typing import Protocol

from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import ProjectExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_player.export.program import Program
from sampletones_player.information import ProgramText


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
    """A backend writing console programs in one format, which binds a run to the program a setup chose.

    The format it writes, the extension its files take and the room each of a program's lines of
    text has are the backend's own, so a setup opened for any format reads them here.
    """

    @property
    def export_format(self) -> ExportFormat: ...

    @property
    def text(self) -> ProgramText: ...

    def choosing(self, program: Program) -> ExportBackend: ...

    def extension(self, scope: ExportScope) -> str: ...
