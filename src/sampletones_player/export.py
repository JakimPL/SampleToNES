from pathlib import Path
from typing import Final, FrozenSet

from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import (
    SILENT_REPORTER,
    ExportProgress,
    ExportReporter,
    announce,
)
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_player.builder import song_from_sample
from sampletones_player.compression.progress.report import CodecProgress, CodecReporter
from sampletones_player.driver.image import DriverImage
from sampletones_player.nsf.file import write_nsf
from sampletones_player.nsf.information import NSFInformation
from sampletones_shared.paths.extensions import EXT_FILE_NSF

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(
    {
        ExportScope.INSTRUMENT,
        ExportScope.SAMPLE,
    }
)

NO_ARTIST: Final[str] = ""
WHOLE_ENVELOPE: None = None
NOTHING_DONE: Final[int] = 0
ONE_FILE: Final[int] = 1
UNMEASURED: None = None


def _compressing(report: ExportReporter) -> CodecReporter:
    """The codec's own reckoning, said in the words an export reports itself in.

    A codec run ends when no further phrase pays for itself, which the song decides rather than
    the caller, so what it offers is the bytes it has laid down so far and no length to measure
    them against.

    Args:
        report: Hears each stage of the export, and answers whether it goes on.

    Returns:
        CodecReporter: What the compression tells the export about itself.
    """

    def reached(progress: CodecProgress) -> bool:
        return report(
            ExportProgress(
                stage=ExportStage.COMPRESSING,
                completed=progress.size,
                total=UNMEASURED,
            )
        )

    return reached


class NSFBackend:
    """Writes the ``.nsf`` files NES sound players and the console itself play.

    An NSF carries its own driver, so the file plays the reconstruction rather than describing
    it to a program that does: every channel slice sounds at once on the channel it was
    reconstructed for, at the rate it was built at and in the tuning it was built with. One file
    holds one song, so a reconstruction and a single slice each become a program of their own,
    the slice sounding on its channel alone.

    The console's program area bounds how long a song may run, and one outgrowing it is reported
    rather than written short.

    Every file carries the same assembled driver, which the backend reads once as it is built.
    A build shipping without it therefore reports itself where the backends are composed, and
    an export spends its reads on the song alone.
    """

    def __init__(self) -> None:
        """Reads the driver every written file carries.

        Raises:
            OSError: If the packaged driver is absent.
            ValueError: If the packaged driver lays out something other than the addresses it
                is built to answer at.
        """
        self._image = DriverImage.load()

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
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Writes a program playing one channel slice.

        Raises:
            OperationCancelled: If ``report`` withdraws the write.
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
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Writes a program playing every channel slice of one reconstruction together.

        The slices are sounded out tick by tick, the ticks are compressed to what the console
        has room for, and the file is written; each of those says so as it starts, so a run of
        seconds reads as the work it is doing.

        Raises:
            OperationCancelled: If ``report`` withdraws the write.
            SongTooLargeError: If the reconstruction runs longer than the program area holds.
            OSError: If the destination cannot be written.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        announce(report, ExportStage.WALKING, NOTHING_DONE, UNMEASURED)
        song = song_from_sample(request, _compressing(report))

        announce(report, ExportStage.WRITING, NOTHING_DONE, ONE_FILE)
        write_nsf(
            destination,
            song,
            NSFInformation(
                title=request.name,
                artist=NO_ARTIST,
            ),
            self._image,
        )
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Reports that a program plays one reconstruction.

        Raises:
            NotImplementedError: Always, until a song flattens to the four streams a program plays.
        """
        raise NotImplementedError("An NSF plays one reconstruction; a whole song reaches the console later")
