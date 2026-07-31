from pathlib import Path
from typing import Any, Final, List, Optional, Tuple
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.trackers.artifact import ExportArtifact
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.trackers.scope import DestinationKind, ExportScope

NES_FREQUENCY: Final[int] = 60


class StubBackend:
    """Records what the service asked for and returns a prepared artefact.

    The service under test owns the thread boundary and the result contract; what lands
    on disk belongs to the real backends and is exercised in their own tests.
    """

    def __init__(
        self,
        truncation: Optional[EnvelopeTruncation] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        self.truncation = truncation
        self.exception = exception
        self.calls: List[Tuple[str, Path, Any]] = []

    @property
    def tracker_format(self) -> TrackerFormat:
        return TrackerFormat.FAMITRACKER

    @property
    def supported_scopes(self) -> frozenset:
        return frozenset(ExportScope)

    def destination_kind(self, scope: ExportScope) -> DestinationKind:
        return DestinationKind.FILE

    def extension(self, scope: ExportScope) -> str:
        return ".fti"

    def write_instrument(self, destination: Path, request: InstrumentExport) -> ExportArtifact:
        return self._write("instrument", destination, request)

    def write_sample(self, destination: Path, request: SampleExport) -> ExportArtifact:
        return self._write("sample", destination, request)

    def write_project(self, destination: Path, request: ProjectExport) -> ExportArtifact:
        return self._write("project", destination, request)

    def _write(self, scope: str, destination: Path, request: Any) -> ExportArtifact:
        self.calls.append((scope, destination, request))
        if self.exception is not None:
            raise self.exception
        return ExportArtifact(paths=(destination,), truncation=self.truncation)


def build_instrument(name: str = "Lead") -> InstrumentExport:
    return InstrumentExport(
        name=name,
        generator=GeneratorName.PULSE1,
        features=Features(
            initial_pitch=60,
            volume=np.full(8, 15, dtype=int),
            arpeggio=np.zeros(8, dtype=int),
            pitch=None,
            hi_pitch=None,
            duty_cycle=None,
        ),
        loop=False,
        nes_frequency=NES_FREQUENCY,
    )


def build_sample(count: int = 2) -> SampleExport:
    return SampleExport(
        name="Kick",
        instruments=tuple(build_instrument(f"Kick {index}") for index in range(count)),
        nes_frequency=NES_FREQUENCY,
    )


@pytest.fixture
def service():
    export_service = ExportService()
    results: List[Any] = []
    export_service.subscribe(results.append)
    return export_service, results


class TestExportWav:
    def test_success_emits_export_success(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "track.wav"

        with patch("sampletones_application.services.export.service.write_wave"):
            export_service.export_wav(filepath, 44100, np.zeros(100))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.WAV
        assert result.filepath == filepath

    def test_success_calls_write_wave_with_correct_args(self, service, tmp_path) -> None:
        export_service, _ = service
        filepath = tmp_path / "track.wav"
        audio = np.zeros(100)

        with patch("sampletones_application.services.export.service.write_wave") as mock_write:
            export_service.export_wav(filepath, 44100, audio)

        mock_write.assert_called_once_with(filepath, 44100, audio)

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "track.wav"
        exception = OSError("disk full")

        with patch("sampletones_application.services.export.service.write_wave", side_effect=exception):
            export_service.export_wav(filepath, 44100, np.zeros(100))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.WAV
        assert result.exception is exception

    def test_error_does_not_emit_success(self, service, tmp_path) -> None:
        export_service, results = service

        with patch(
            "sampletones_application.services.export.service.write_wave",
            side_effect=RuntimeError("fail"),
        ):
            export_service.export_wav(tmp_path / "x.wav", 44100, np.zeros(10))

        assert not any(isinstance(r, ExportSuccess) for r in results)


class TestExportInstrument:
    def test_success_emits_export_success(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "instrument.fti"

        export_service.export_instrument(filepath, StubBackend(), build_instrument())

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.INSTRUMENT
        assert result.filepath == filepath

    def test_the_backend_receives_the_destination_and_the_request(self, service, tmp_path) -> None:
        export_service, _ = service
        filepath = tmp_path / "instrument.fti"
        backend = StubBackend()
        request = build_instrument("Guitar")

        export_service.export_instrument(filepath, backend, request)

        assert backend.calls == [("instrument", filepath, request)]

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        exception = PermissionError("read-only")

        export_service.export_instrument(
            tmp_path / "instrument.fti",
            StubBackend(exception=exception),
            build_instrument(),
        )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.INSTRUMENT
        assert result.exception is exception

    def test_error_does_not_emit_success(self, service, tmp_path) -> None:
        export_service, results = service

        export_service.export_instrument(
            tmp_path / "x.fti",
            StubBackend(exception=OSError("fail")),
            build_instrument(),
        )

        assert not any(isinstance(r, ExportSuccess) for r in results)


class TestExportSample:
    def test_success_emits_export_success_with_the_destination(self, service, tmp_path) -> None:
        export_service, results = service

        export_service.export_sample(tmp_path, StubBackend(), build_sample())

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.INSTRUMENTS
        assert result.filepath == tmp_path

    def test_the_backend_receives_every_slice_in_one_call(self, service, tmp_path) -> None:
        export_service, _ = service
        backend = StubBackend()
        request = build_sample(3)

        export_service.export_sample(tmp_path, backend, request)

        assert backend.calls == [("sample", tmp_path, request)]

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        exception = OSError("no space")

        export_service.export_sample(tmp_path, StubBackend(exception=exception), build_sample())

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.INSTRUMENTS
        assert result.exception is exception

    def test_a_sample_with_no_slices_emits_success(self, service, tmp_path) -> None:
        export_service, results = service

        export_service.export_sample(tmp_path, StubBackend(), build_sample(0))

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.INSTRUMENTS


class TestExportTruncationReporting:
    def test_a_complete_instrument_reports_no_truncation(self, service, tmp_path) -> None:
        export_service, results = service

        export_service.export_instrument(tmp_path / "inst.fti", StubBackend(), build_instrument())

        assert results[0].truncation is None

    def test_a_shortened_instrument_carries_the_backend_report(self, service, tmp_path) -> None:
        export_service, results = service
        truncation = EnvelopeTruncation(frames=252, source_frames=300, instruments=1)

        export_service.export_instrument(
            tmp_path / "inst.fti",
            StubBackend(truncation=truncation),
            build_instrument(),
        )

        assert results[0].truncation == truncation

    def test_a_shortened_sample_carries_the_backend_report(self, service, tmp_path) -> None:
        export_service, results = service
        truncation = EnvelopeTruncation(frames=252, source_frames=410, instruments=2)

        export_service.export_sample(tmp_path, StubBackend(truncation=truncation), build_sample(3))

        assert results[0].truncation == truncation

    def test_a_wav_export_reports_no_truncation(self, service, tmp_path) -> None:
        export_service, results = service

        with patch("sampletones_application.services.export.service.write_wave"):
            export_service.export_wav(tmp_path / "track.wav", 44100, np.zeros(100))

        assert results[0].truncation is None


class TestExportServiceConcurrency:
    def test_second_export_while_first_running_is_rejected(self, tmp_path) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        with patch.object(export_service._executor, "execute", return_value=False):
            export_service.export_wav(tmp_path / "track.wav", 44100, np.zeros(10))

        assert results == []

    def test_multiple_simultaneous_calls_do_not_stack_up(self, tmp_path) -> None:
        export_service = ExportService()
        call_count = 0

        def on_result(result: Any) -> None:
            nonlocal call_count
            call_count += 1

        export_service.subscribe(on_result)

        with patch.object(export_service._executor, "execute", return_value=False):
            for _ in range(5):
                export_service.export_wav(tmp_path / "track.wav", 44100, np.zeros(10))

        assert call_count == 0
