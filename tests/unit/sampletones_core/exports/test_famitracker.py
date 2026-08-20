from pathlib import Path
from typing import Final, Optional

import numpy as np
import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.implementation.famitracker import FamiTrackerBackend
from sampletones_core.exports.request import InstrumentExport, SampleExport
from sampletones_core.exports.scope import ExportScope
from sampletones_core.formats.famitracker.specification.sequences import (
    MAX_SEQUENCE_ITEMS,
)
from sampletones_shared.music import Tuning
from sampletones_shared.paths.extensions import EXT_FILE_INSTRUMENT, EXT_FILE_MODULE

NES_FREQUENCY: Final[int] = 60


def build_features(frames: int, *, duty_cycle_frames: Optional[int] = None) -> Features:
    duty_cycle = None if duty_cycle_frames is None else np.zeros(duty_cycle_frames, dtype=int)
    return Features(
        initial_pitch=60,
        volume=np.full(frames, 15, dtype=int),
        arpeggio=np.zeros(frames, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=duty_cycle,
    )


def build_instrument(name: str, frames: int) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        channel=ChannelName.PULSE1,
        features=build_features(frames),
        loop=False,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


def build_sample(name: str, *instruments: InstrumentExport) -> SampleExport:
    return SampleExport(
        name=name,
        instruments=instruments,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


@pytest.fixture(name="backend")
def backend_fixture() -> FamiTrackerBackend:
    return FamiTrackerBackend()


class TestFormatDeclaration:
    def test_the_backend_names_its_format(self, backend: FamiTrackerBackend) -> None:
        assert backend.export_format == ExportFormat.FAMITRACKER

    def test_every_scope_is_supported(self, backend: FamiTrackerBackend) -> None:
        assert backend.supported_scopes == frozenset(ExportScope)

    @pytest.mark.parametrize(
        ("scope", "expected"),
        [
            (ExportScope.INSTRUMENT, EXT_FILE_INSTRUMENT),
            (ExportScope.SAMPLE, EXT_FILE_INSTRUMENT),
            (ExportScope.PROJECT, EXT_FILE_MODULE),
        ],
    )
    def test_instruments_carry_the_instrument_extension_and_a_project_the_module_one(
        self,
        backend: FamiTrackerBackend,
        scope: ExportScope,
        expected: str,
    ) -> None:
        assert backend.extension(scope) == expected


class TestWriteInstrument:
    def test_the_file_is_written_and_reported(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Short{EXT_FILE_INSTRUMENT}"

        artifact = backend.write_instrument(destination, build_instrument("Short", 16))

        assert destination.exists()
        assert artifact.paths == (destination,)

    def test_an_envelope_within_the_limit_reports_nothing(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        artifact = backend.write_instrument(
            tmp_path / f"Short{EXT_FILE_INSTRUMENT}",
            build_instrument("Short", MAX_SEQUENCE_ITEMS),
        )
        assert artifact.truncation is None

    def test_an_envelope_beyond_the_limit_reports_both_counts(
        self,
        backend: FamiTrackerBackend,
        tmp_path: Path,
    ) -> None:
        artifact = backend.write_instrument(
            tmp_path / f"Long{EXT_FILE_INSTRUMENT}",
            build_instrument("Long", 300),
        )
        assert artifact.truncation == EnvelopeTruncation(
            frames=MAX_SEQUENCE_ITEMS,
            source_frames=300,
            instruments=1,
        )

    def test_a_shortened_export_still_writes_the_file(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Long{EXT_FILE_INSTRUMENT}"
        backend.write_instrument(destination, build_instrument("Long", 300))
        assert destination.exists()


class TestWriteSample:
    def test_each_slice_lands_beside_the_destination_named_after_its_instrument(
        self,
        backend: FamiTrackerBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / f"Kick{EXT_FILE_INSTRUMENT}"
        request = build_sample(
            "Kick",
            build_instrument("Kick (pulse1)", 16),
            build_instrument("Kick (noise)", 16),
        )

        artifact = backend.write_sample(destination, request)

        assert artifact.paths == (
            tmp_path / f"Kick (pulse1){EXT_FILE_INSTRUMENT}",
            tmp_path / f"Kick (noise){EXT_FILE_INSTRUMENT}",
        )
        assert all(path.exists() for path in artifact.paths)

    def test_a_missing_directory_is_created(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        destination = tmp_path / "nested" / f"Kick{EXT_FILE_INSTRUMENT}"

        backend.write_sample(destination, build_sample("Kick", build_instrument("Kick", 16)))

        assert destination.parent.is_dir()

    def test_the_report_spans_every_shortened_slice(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        request = build_sample(
            "Kick",
            build_instrument("Short", 16),
            build_instrument("Long", 300),
            build_instrument("Longer", 410),
        )

        artifact = backend.write_sample(tmp_path / "Kick", request)

        assert artifact.truncation == EnvelopeTruncation(
            frames=MAX_SEQUENCE_ITEMS,
            source_frames=410,
            instruments=2,
        )

    def test_slices_that_all_fit_report_nothing(self, backend: FamiTrackerBackend, tmp_path: Path) -> None:
        request = build_sample("Kick", build_instrument("Short", 16))

        artifact = backend.write_sample(tmp_path / "Kick", request)

        assert artifact.truncation is None
