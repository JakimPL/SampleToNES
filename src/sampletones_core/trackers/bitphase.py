from pathlib import Path
from typing import FrozenSet, List

from sampletones_core.bitphase.btp import write_btp
from sampletones_core.bitphase.builder import (
    instrument_to_bitphase,
    project_to_bitphase,
    sample_to_bitphase,
)
from sampletones_core.bitphase.preset import instrument_to_preset, write_preset
from sampletones_core.paths import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_core.trackers.artifact import ExportArtifact
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.request import InstrumentExport, ProjectExport, SampleExport
from sampletones_core.trackers.scope import DestinationKind, ExportScope

DOCUMENT_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)
PRESET_SCOPES: FrozenSet[ExportScope] = frozenset({ExportScope.INSTRUMENT, ExportScope.SAMPLE})

WHOLE_ENVELOPE: None = None


class BitphaseBackend:
    """Writes Bitphase's ``.btp`` documents.

    A ``.btp`` holds a whole document, so every scope lands in one file: an instrument
    and a reconstruction each become a playable document whose pattern triggers the
    instruments it carries. Bitphase stores instrument and table rows without a length
    limit, so every envelope crosses over whole.
    """

    @property
    def tracker_format(self) -> TrackerFormat:
        return TrackerFormat.BITPHASE

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return DOCUMENT_SCOPES

    def destination_kind(self, scope: ExportScope) -> DestinationKind:
        return DestinationKind.FILE

    def extension(self, scope: ExportScope) -> str:
        return EXT_FILE_BITPHASE

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
    ) -> ExportArtifact:
        write_btp(destination, instrument_to_bitphase(request))
        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
    ) -> ExportArtifact:
        write_btp(destination, sample_to_bitphase(request))
        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
    ) -> ExportArtifact:
        write_btp(destination, project_to_bitphase(request.project))
        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)


class BitphasePresetBackend:
    """Writes the single-instrument ``.json`` files Bitphase's instruments panel loads.

    The panel reads one instrument per file into the slot the user has selected, so a
    whole reconstruction lands as a directory of them, one file per generator slice
    named after the instrument. A preset carries rows alone, so its pitch contour rides
    in each row's tone offset.
    """

    @property
    def tracker_format(self) -> TrackerFormat:
        return TrackerFormat.BITPHASE_PRESET

    @property
    def supported_scopes(self) -> FrozenSet[ExportScope]:
        return PRESET_SCOPES

    def destination_kind(self, scope: ExportScope) -> DestinationKind:
        return DestinationKind.DIRECTORY if scope == ExportScope.SAMPLE else DestinationKind.FILE

    def extension(self, scope: ExportScope) -> str:
        return EXT_FILE_JSON

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
    ) -> ExportArtifact:
        write_preset(destination, instrument_to_preset(request))
        return ExportArtifact(paths=(destination,), truncation=WHOLE_ENVELOPE)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
    ) -> ExportArtifact:
        destination.mkdir(parents=True, exist_ok=True)

        paths: List[Path] = []
        for instrument in request.instruments:
            filepath = destination / f"{instrument.name}{EXT_FILE_JSON}"
            paths.extend(self.write_instrument(filepath, instrument).paths)

        return ExportArtifact(paths=tuple(paths), truncation=WHOLE_ENVELOPE)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
    ) -> ExportArtifact:
        """Reports that a preset holds one instrument.

        Raises:
            ValueError: Always, since a preset file carries a single instrument.
        """
        raise ValueError("A Bitphase instrument preset holds one instrument, not a whole project")
