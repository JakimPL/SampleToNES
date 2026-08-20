from pathlib import Path
from typing import Final, FrozenSet

from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_player.builder import song_from_sample
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


class NSFBackend:
    """Writes the ``.nsf`` files NES sound players and the console itself play.

    An NSF carries its own driver, so the file plays the reconstruction rather than describing
    it to a program that does: every channel slice sounds at once on the channel it was
    reconstructed for, at the rate it was built at and in the tuning it was built with. One file
    holds one song, so a reconstruction and a single slice each become a program of their own,
    the slice sounding on its channel alone.

    The console's program area bounds how long a song may run, and one outgrowing it is reported
    rather than written short.
    """

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.NSF

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return SUPPORTED_SCOPES

    def extension(self, scope: ExportScope) -> str:
        return EXT_FILE_NSF

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
    ) -> ExportArtifact:
        """Writes a program playing one channel slice.

        Raises:
            SongTooLargeError: If the slice runs longer than the program area holds.
            OSError: If the destination cannot be written.
        """
        sample = SampleExport(
            name=request.name,
            instruments=(request,),
            nes_frequency=request.nes_frequency,
            tuning=request.tuning,
        )
        return self.write_sample(destination, sample)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
    ) -> ExportArtifact:
        """Writes a program playing every channel slice of one reconstruction together.

        Raises:
            SongTooLargeError: If the reconstruction runs longer than the program area holds.
            OSError: If the destination cannot be written.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_nsf(
            destination,
            song_from_sample(request),
            NSFInformation(
                title=request.name,
                artist=NO_ARTIST,
            ),
        )

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
    ) -> ExportArtifact:
        """Reports that a program plays one reconstruction.

        Raises:
            NotImplementedError: Always, until a song flattens to the four streams a program plays.
        """
        raise NotImplementedError("An NSF plays one reconstruction; a whole song reaches the console later")
