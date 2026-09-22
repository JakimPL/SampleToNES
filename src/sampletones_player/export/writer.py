from pathlib import Path
from typing import Final, Self

from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.progress import ExportReporter, announce
from sampletones_core.exports.request import SampleExport
from sampletones_core.exports.stage import ExportStage
from sampletones_core.project.project import Project
from sampletones_player.builder import song_from_project, song_from_sample
from sampletones_player.driver.image import DriverImage
from sampletones_player.export.program import NSFProgram
from sampletones_player.export.reports import (
    UNMEASURED,
    codec_reporter,
    walk_reporter,
)
from sampletones_player.nsf.file import write_nsf
from sampletones_player.song import Song

WHOLE_ENVELOPE: None = None
NOTHING_DONE: Final[int] = 0
ONE_FILE: Final[int] = 1


class NSFWriter:
    """Lays a program down on disk: its song played out, compressed, and written behind the driver.

    Each of those says so as it starts, so a run of seconds reads as the work it is doing, and the
    program states every choice the file carries — the channels the song sounds, where it repeats,
    how hard it is compressed and the text it is listed under.

    Every file carries the same assembled driver, which the writer holds from the moment it is
    built, so a run spends its reads on the song alone.
    """

    def __init__(self, image: DriverImage) -> None:
        self._image = image

    @classmethod
    def load(cls) -> Self:
        """Builds the writer over the driver the package ships.

        Raises:
            OSError: If the packaged driver is absent.
            ValueError: If the packaged driver lays out something other than the addresses it
                is built to answer at.
        """
        return cls(DriverImage.load())

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        program: NSFProgram,
        report: ExportReporter,
    ) -> ExportArtifact:
        """Writes a program playing a reconstruction's slices together.

        Args:
            destination: The file to write.
            request: The slices to play.
            program: The choices the file carries.
            report: Hears each stage of the write, and answers whether it goes on.

        Returns:
            ExportArtifact: The file written.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the song holds more than the program area has room for.
            OSError: If the destination cannot be written.
            ValueError: If the program's loop tick lies outside the song.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        announce(report, ExportStage.WALKING, NOTHING_DONE, UNMEASURED)
        song = song_from_sample(
            request,
            channels=program.channels,
            loop_tick=program.loop_tick,
            scheme=program.scheme,
            report=codec_reporter(report),
        )
        return self._write(destination, song, program, report)

    def write_project(
        self,
        destination: Path,
        project: Project,
        program: NSFProgram,
        report: ExportReporter,
    ) -> ExportArtifact:
        """Writes a program playing a whole composition.

        The arrangement is played out row by row into the ticks each channel sounds, and the walk
        reads as a fraction of the song it is playing out.

        Args:
            destination: The file to write.
            project: The composition to play.
            program: The choices the file carries.
            report: Hears each stage of the write, and answers whether it goes on.

        Returns:
            ExportArtifact: The file written.

        Raises:
            OperationCanceled: If ``report`` withdraws the write.
            SongTooLargeError: If the song holds more than the program area has room for.
            OSError: If the destination cannot be written.
            ValueError: If the program's loop tick lies outside the song, or the project's samples
                were reconstructed against tunings that differ.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        song = song_from_project(
            project,
            channels=program.channels,
            loop_tick=program.loop_tick,
            scheme=program.scheme,
            report=codec_reporter(report),
            walk=walk_reporter(report),
        )
        return self._write(destination, song, program, report)

    def _write(
        self,
        destination: Path,
        song: Song,
        program: NSFProgram,
        report: ExportReporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_DONE, ONE_FILE)
        write_nsf(destination, song, program.information, self._image)
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)
        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE, skipped_rows=NO_SKIPPED_ROWS)
