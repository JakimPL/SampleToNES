from pathlib import Path
from typing import FrozenSet, List, Optional

from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.formats.famitracker.export import write_ftm
from sampletones_core.formats.famitracker.instrument import write_fti
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.sequences.features import features_to_instrument_sequences
from sampletones_core.formats.famitracker.specification.instruments import STANDALONE_INSTRUMENT_INDEX
from sampletones_core.formats.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS
from sampletones_core.paths import EXT_FILE_INSTRUMENT, EXT_FILE_MODULE
from sampletones_core.trackers.artifact import ExportArtifact
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.trackers.scope import ExportScope

SUPPORTED_SCOPES: FrozenSet[ExportScope] = frozenset(ExportScope)


class FamiTrackerBackend:
    """Writes FamiTracker's ``.fti`` instruments and ``.ftm`` modules.

    FamiTracker reads one instrument per ``.fti`` file, so a whole reconstruction lands
    as a set of them beside the chosen destination, one file per generator slice named
    after the instrument.
    """

    @property
    def tracker_format(self) -> TrackerFormat:
        return TrackerFormat.FAMITRACKER

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
        features = request.features
        sequences = features_to_instrument_sequences(
            volume=features.volume,
            arpeggio=features.arpeggio,
            pitch=features.pitch,
            hi_pitch=features.hi_pitch,
            duty_cycle=features.duty_cycle,
            loop=request.loop,
        )
        instrument = Instrument2A03(
            index=STANDALONE_INSTRUMENT_INDEX,
            name=request.name,
            sequences=sequences,
        )
        write_fti(destination, instrument)

        return ExportArtifact(
            paths=(destination,),
            truncation=EnvelopeTruncation.measure(
                features.frame_count,
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
            filepath = destination.with_name(f"{instrument.name}{EXT_FILE_INSTRUMENT}")
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
