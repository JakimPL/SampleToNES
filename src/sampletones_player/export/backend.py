from __future__ import annotations

from pathlib import Path
from typing import FrozenSet

from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import ExportReporter
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_player.export.choice import ProgramChoice
from sampletones_player.export.chosen import ChosenProgram
from sampletones_player.export.container import ProgramContainer
from sampletones_player.export.program import Program
from sampletones_player.export.stated import StatedProgram
from sampletones_player.export.writer import ProgramWriter
from sampletones_player.information import TextLine
from sampletones_shared.utils.progress import silent_reporter

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(
    {
        ExportScope.INSTRUMENT,
        ExportScope.SAMPLE,
        ExportScope.PROJECT,
    }
)


class ProgramBackend:
    """Writes the programs the console itself runs, in the kind of file its container lays out.

    A program carries its own driver, so the file itself plays the reconstruction: every channel
    slice sounds at once on the channel it was reconstructed for, at the rate it was built at and
    in the tuning it was built with. One file holds one song, so a reconstruction and a single
    slice each become a program of their own, the slice sounding on its channel alone.

    What the program states beyond its song — the channels, the repeat, the compression and the
    text — is a :class:`ProgramChoice`. The backend the application registers writes each request
    as its source states; :meth:`choosing` answers with one writing the program a user settled.
    The format, the extension and the room the text has are the container's own.

    The file bounds how long a song may run, and a song outgrowing it is reported as too large.
    """

    def __init__(
        self,
        container: ProgramContainer,
        choice: ProgramChoice,
    ) -> None:
        self._container = container
        self._writer = ProgramWriter(container)
        self._choice = choice

    @classmethod
    def stated(cls, container: ProgramContainer) -> ProgramBackend:
        """The backend writing each request into ``container`` as the program its own source states.

        Args:
            container: The kind of file the backend writes.

        Returns:
            ProgramBackend: The backend the application registers for the container's format.
        """
        return cls(container, StatedProgram())

    def choosing(self, program: Program) -> ProgramBackend:
        """The backend writing every request as ``program``, into the container this one holds.

        Args:
            program: The choices the file carries.

        Returns:
            ProgramBackend: The backend to hand the run.
        """
        return ProgramBackend(self._container, ChosenProgram(program))

    @property
    def export_format(self) -> ExportFormat:
        return self._container.export_format

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return SUPPORTED_SCOPES

    @property
    def text(self) -> TextLine:
        """The room each line of a program's text has in the files this backend writes."""
        return self._container.text

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return self._container.extension

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        """Writes a program playing one channel slice.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the slice runs longer than the file holds.
            OSError: If the destination cannot be written.
        """
        sample = SampleExport(
            name=request.name,
            instruments=(request,),
            nes_frequency=request.nes_frequency,
            tuning=request.tuning,
        )
        return self.write_sample(destination, sample, report)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        """Writes a program playing every channel slice of one reconstruction together.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the reconstruction runs longer than the file holds.
            OSError: If the destination cannot be written.
            ValueError: If the program's loop tick lies outside the song.
        """
        return self._writer.write_sample(
            destination,
            request,
            self._choice.for_sample(request),
            report,
        )

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        """Writes a program playing a whole composition.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the song holds more than the file has room for.
            OSError: If the destination cannot be written.
            ValueError: If the program's loop tick lies outside the song, or the project's samples
                were reconstructed against tunings that differ.
        """
        return self._writer.write_project(
            destination,
            request.project,
            self._choice.for_project(request.project),
            report,
        )
