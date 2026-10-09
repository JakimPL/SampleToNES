from pathlib import Path
from typing import Final, FrozenSet

from sampletones_core.exporters.skipped import NO_SKIPPED_ROWS
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.batch import write_instrument_files
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import ExportReporter, announce
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_core.formats.bitphase.btp import write_btp
from sampletones_core.formats.bitphase.builder import (
    build_bitphase,
    instrument_to_bitphase,
    sample_to_bitphase,
)
from sampletones_core.formats.bitphase.preset import instrument_to_preset, write_preset
from sampletones_core.formats.bitphase.truncation import document_truncation, preset_truncation
from sampletones_shared.paths.extensions import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_shared.utils.progress import silent_reporter

DOCUMENT_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)
PRESET_SCOPES: FrozenSet[ExportScope] = frozenset({ExportScope.INSTRUMENT, ExportScope.SAMPLE})

NOTHING_WRITTEN: Final[int] = 0
ONE_FILE: Final[int] = 1


class BitphaseBackend:
    """Writes Bitphase's ``.btp`` documents.

    A ``.btp`` holds a whole document, so every scope lands in one file: an instrument
    and a reconstruction each become a playable document whose pattern triggers the
    instruments it carries. A macro holds the values of one dimension, up to the 512 a
    Bitphase instrument stores, and a table carries a contour of any length. Every scope
    reports the instruments a macro shortened.
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
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_btp(destination, instrument_to_bitphase(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(
            paths=(destination,),
            truncation=document_truncation(request.features),
            skipped_rows=NO_SKIPPED_ROWS,
        )

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_btp(destination, sample_to_bitphase(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(
            paths=(destination,),
            truncation=EnvelopeTruncation.summarize(
                [document_truncation(instrument.features) for instrument in request.instruments],
            ),
            skipped_rows=NO_SKIPPED_ROWS,
        )

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        built = build_bitphase(request.project)
        write_btp(destination, built.document)
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(
            paths=(destination,),
            truncation=built.truncation,
            skipped_rows=built.skipped_rows,
        )


class BitphasePresetBackend:
    """Writes the single-instrument ``.json`` files Bitphase's instruments panel loads.

    The panel reads one instrument per file into the slot the user has selected, so a
    whole reconstruction lands as a set of them beside the chosen destination, one file
    per channel slice named after the instrument. A preset carries macros alone, so its
    pitch contour rides in the tone offset each tick takes, and every dimension, the contour
    among them, keeps the values a macro holds. Every scope reports the instruments a macro
    shortened.
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
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        write_preset(destination, instrument_to_preset(request))
        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)

        return ExportArtifact(
            paths=(destination,),
            truncation=preset_truncation(request.features),
            skipped_rows=NO_SKIPPED_ROWS,
        )

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        return write_instrument_files(
            destination,
            request,
            report,
            extension=EXT_FILE_JSON,
            write_instrument=self.write_instrument,
        )

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = silent_reporter,
    ) -> ExportArtifact:
        """Reports that a preset holds one instrument.

        Raises:
            ValueError: Always, since a preset file carries a single instrument.
        """
        raise ValueError("A Bitphase instrument preset holds one instrument, not a whole project")
