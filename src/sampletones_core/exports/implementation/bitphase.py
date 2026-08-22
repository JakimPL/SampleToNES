from pathlib import Path
from typing import Final, FrozenSet, List

from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import SILENT_REPORTER, ExportReporter, announce
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import (
    instrument_to_bitphase,
    project_to_bitphase,
    sample_to_bitphase,
)
from sampletones_core.formats.bitphase.preset import instrument_to_preset, write_preset
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_shared.utils.system.paths import get_filename

DOCUMENT_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)
PRESET_SCOPES: FrozenSet[ExportScope] = frozenset({ExportScope.INSTRUMENT, ExportScope.SAMPLE})

WHOLE_ENVELOPE: None = None
NOTHING_WRITTEN: Final[int] = 0
ONE_FILE: Final[int] = 1


class BitphaseBackend:
    """Writes Bitphase's ``.btp`` documents.

    A ``.btp`` holds a whole document, so every scope lands in one file: an instrument
    and a reconstruction each become a playable document whose pattern triggers the
    instruments it carries. Bitphase stores instrument and table rows without a length
    limit, so every envelope crosses over whole.
    """

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.BITPHASE

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return DOCUMENT_SCOPES

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return EXT_FILE_BITPHASE

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_btp(destination, instrument_to_bitphase(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_btp(destination, sample_to_bitphase(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_btp(destination, project_to_bitphase(request.project))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)


class BitphasePresetBackend:
    """Writes the single-instrument ``.json`` files Bitphase's instruments panel loads.

    The panel reads one instrument per file into the slot the user has selected, so a
    whole reconstruction lands as a set of them beside the chosen destination, one file
    per channel slice named after the instrument. A preset carries rows alone, so its
    pitch contour rides in each row's tone offset.
    """

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.BITPHASE_PRESET

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return PRESET_SCOPES

    def extension(self, scope: ExportScope) -> str:  # pylint: disable=unused-argument
        return EXT_FILE_JSON

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_preset(destination, instrument_to_preset(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        destination.parent.mkdir(parents=True, exist_ok=True)

        written = len(request.instruments)
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, written)

        paths: List[Path] = []
        for index, instrument in enumerate(request.instruments, start=ONE_FILE):
            filepath = destination.with_name(
                get_filename(
                    instrument.name,
                    EXT_FILE_JSON,
                )
            )
            paths.extend(self.write_instrument(filepath, instrument, SILENT_REPORTER).paths)
            announce(report, ExportStage.WRITING, index, written)

        return ExportArtifact(paths=tuple(paths), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        """Reports that a preset holds one instrument.

        Raises:
            ValueError: Always, since a preset file carries a single instrument.
        """
        raise ValueError("A Bitphase instrument preset holds one instrument, not a whole project")
