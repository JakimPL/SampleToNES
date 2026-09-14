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
from sampletones_player.export.program import NSFProgram
from sampletones_player.export.stated import StatedProgram
from sampletones_player.export.writer import NSFWriter
from sampletones_shared.paths.extensions import EXT_FILE_NSF
from sampletones_shared.utils.progress import silent_reporter

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(
    {
        ExportScope.INSTRUMENT,
        ExportScope.SAMPLE,
        ExportScope.PROJECT,
    }
)


class NSFBackend:
    """Writes the ``.nsf`` files NES sound players and the console itself play.

    An NSF carries its own driver, so the file plays the reconstruction rather than describing
    it to a program that does: every channel slice sounds at once on the channel it was
    reconstructed for, at the rate it was built at and in the tuning it was built with. One file
    holds one song, so a reconstruction and a single slice each become a program of their own,
    the slice sounding on its channel alone.

    What the program states beyond its song — the channels, the repeat, the compression and the
    text — is a :class:`ProgramChoice`. The backend the application registers writes each request
    as its source states; :meth:`choosing` answers with one writing the program a user settled.

    The console's program area bounds how long a song may run, and one outgrowing it is reported
    rather than written short.
    """

    def __init__(
        self,
        writer: NSFWriter,
        choice: ProgramChoice,
    ) -> None:
        self._writer = writer
        self._choice = choice

    @classmethod
    def stated(cls) -> NSFBackend:
        """The backend writing each request as the program its own source states.

        The driver every file carries is read here, so a build shipping without it reports itself
        where the backends are composed.

        Raises:
            OSError: If the packaged driver is absent.
            ValueError: If the packaged driver lays out something other than the addresses it
                is built to answer at.
        """
        return cls(NSFWriter.load(), StatedProgram())

    def choosing(self, program: NSFProgram) -> NSFBackend:
        """The backend writing every request as ``program``, over the driver this one holds.

        Args:
            program: The choices the file carries.

        Returns:
            NSFBackend: The backend to hand the run.
        """
        return NSFBackend(self._writer, ChosenProgram(program))

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.NSF

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return SUPPORTED_SCOPES

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return EXT_FILE_NSF

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        """Writes a program playing one channel slice.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the slice runs longer than the program area holds.
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
            SongTooLargeError: If the reconstruction runs longer than the program area holds.
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
            SongTooLargeError: If the song holds more than the program area has room for.
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
