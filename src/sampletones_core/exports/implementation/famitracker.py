from pathlib import Path
from typing import Final, FrozenSet, List, Optional

from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import ExportReporter, announce
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_core.formats.famitracker.builder import build_instrument
from sampletones_core.formats.famitracker.export import write_ftm
from sampletones_core.formats.famitracker.instrument import write_fti
from sampletones_core.formats.famitracker.sequences.features import features_truncation
from sampletones_core.formats.famitracker.specification.instruments import (
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT, EXT_FILE_MODULE
from sampletones_shared.utils.progress import silent_reporter
from sampletones_shared.utils.system.paths import get_filename

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)

NOTHING_WRITTEN: Final[int] = 0
ONE_FILE: Final[int] = 1


class FamiTrackerBackend:
    """Writes FamiTracker's ``.fti`` instruments and ``.ftm`` modules.

    FamiTracker reads one instrument per ``.fti`` file, so a whole reconstruction lands
    as a set of them beside the chosen destination, one file per channel slice named
    after the instrument.
    """

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.FAMITRACKER

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return SUPPORTED_SCOPES

    def extension(self, scope: ExportScope) -> str:
        return EXT_FILE_MODULE if scope == ExportScope.PROJECT else EXT_FILE_INSTRUMENT

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        instrument = build_instrument(
            STANDALONE_INSTRUMENT_INDEX,
            request.name,
            request.features,
        )
        write_fti(destination, instrument)
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(
            paths=(destination,),
            truncation=features_truncation(request.features),
        )

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        destination.parent.mkdir(parents=True, exist_ok=True)

        written = len(request.instruments)
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, written)

        paths: List[Path] = []
        truncations: List[Optional[EnvelopeTruncation]] = []
        for index, instrument in enumerate(request.instruments, start=ONE_FILE):
            filepath = destination.with_name(
                get_filename(
                    instrument.name,
                    EXT_FILE_INSTRUMENT,
                )
            )
            artifact = self.write_instrument(filepath, instrument, silent_reporter)
            paths.extend(artifact.paths)
            truncations.append(artifact.truncation)
            announce(report, ExportStage.WRITING, index, written)

        return ExportArtifact(
            paths=tuple(paths),
            truncation=EnvelopeTruncation.summarize(truncations),
        )

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_ftm(destination, request.project)
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=None)
