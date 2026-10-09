from pathlib import Path
from typing import Callable, Final, List, Optional

from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.progress import ExportReporter, announce
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.exports.stage import ExportStage
from sampletones_shared.utils.progress import silent_reporter
from sampletones_shared.utils.system.paths import get_filename

NOTHING_WRITTEN: Final[int] = 0
FIRST_FILE: Final[int] = 1

InstrumentWriter = Callable[[Path, InstrumentExport, ExportReporter], ExportArtifact]


def write_instrument_files(
    destination: Path,
    request: SampleExport,
    report: ExportReporter,
    *,
    extension: str,
    write_instrument: InstrumentWriter,
) -> ExportArtifact:
    """Writes every slice of a reconstruction as a file of its own beside ``destination``.

    A format that holds one instrument per file lands a reconstruction as a set of them, each named
    after the instrument it carries. The run counts the files as it writes them, and the report
    gathers what each file left out.

    Args:
        destination: The file the scope was given, which the slices are written beside.
        request: The reconstruction's slices.
        report: Hears each file written, and answers whether the run goes on.
        extension: The extension each file carries, leading dot included.
        write_instrument: Writes one slice to the file it is given.

    Returns:
        ExportArtifact: Every file written, in write order, and the slices shortened.

    Raises:
        OperationCanceled: If ``report`` withdraws the run.
        OSError: If a file cannot be written.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    written = len(request.instruments)
    announce(report, ExportStage.WRITING, NOTHING_WRITTEN, written)

    paths: List[Path] = []
    truncations: List[Optional[EnvelopeTruncation]] = []
    for index, instrument in enumerate(request.instruments, start=FIRST_FILE):
        filepath = destination.with_name(
            get_filename(
                instrument.name,
                extension,
            )
        )
        artifact = write_instrument(filepath, instrument, silent_reporter)
        paths.extend(artifact.paths)
        truncations.append(artifact.truncation)
        announce(report, ExportStage.WRITING, index, written)

    return ExportArtifact(
        paths=tuple(paths),
        truncation=EnvelopeTruncation.summarize(truncations),
        skipped_rows=NO_SKIPPED_ROWS,
    )
