from pathlib import Path
from typing import FrozenSet, List, Optional

from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.formats.famitracker.builder import build_instrument
from sampletones_core.formats.famitracker.export import write_ftm
from sampletones_core.formats.famitracker.instrument import write_fti
from sampletones_core.formats.famitracker.specification.instruments import (
    STANDALONE_INSTRUMENT_INDEX,
)
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
)
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT, EXT_FILE_MODULE
from sampletones_shared.utils.system.paths import get_filename

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)


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
    ) -> ExportArtifact:
        instrument = build_instrument(
            STANDALONE_INSTRUMENT_INDEX,
            request.name,
            request.features,
            loop=request.loop,
        )
        write_fti(destination, instrument)

        return ExportArtifact(
            paths=(destination,),
            truncation=EnvelopeTruncation.measure(
                request.features.frame_count,
                MAX_SEQUENCE_ITEMS,
            ),
        )

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
    ) -> ExportArtifact:
        destination.parent.mkdir(parents=True, exist_ok=True)

        paths: List[Path] = []
        truncations: List[Optional[EnvelopeTruncation]] = []
        for instrument in request.instruments:
            filepath = destination.with_name(
                get_filename(
                    instrument.name,
                    EXT_FILE_INSTRUMENT,
                )
            )
            artifact = self.write_instrument(filepath, instrument)
            paths.extend(artifact.paths)
            truncations.append(artifact.truncation)

        return ExportArtifact(
            paths=tuple(paths),
            truncation=EnvelopeTruncation.summarize(truncations),
        )

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
    ) -> ExportArtifact:
        write_ftm(destination, request.project)
        return ExportArtifact(paths=(destination,), truncation=None)
