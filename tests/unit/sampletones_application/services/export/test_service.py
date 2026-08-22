from pathlib import Path
from typing import Any, Callable, Final, List, Optional, Tuple
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceProgress,
    ServiceStarted,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.artifact import ExportArtifact
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.progress import (
    SILENT_REPORTER,
    ExportReporter,
    announce,
)
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.scope import ExportScope
from sampletones_core.exports.stage import ExportStage
from sampletones_core.project.project import Project
from sampletones_shared.music import Tuning

NES_FREQUENCY: Final[int] = 60
NOTHING_WRITTEN: Final[int] = 0
ONE_FILE: Final[int] = 1


def outcome(results: List[Any]) -> Any:
    """The result a run finished on, which follows whatever it said while it ran."""
    return results[-1]


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
        self.on_write: Optional[Callable[[], None]] = None

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.FAMITRACKER

    @property
    def supported_scopes(self) -> frozenset:
        return frozenset(ExportScope)

    def extension(self, scope: ExportScope) -> str:
        return ".fti"

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        return self._write("instrument", destination, request, report)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        return self._write("sample", destination, request, report)

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        return self._write("project", destination, request, report)

    def _write(
        self,
        scope: str,
        destination: Path,
        request: Any,
        report: ExportReporter,
    ) -> ExportArtifact:
        self.calls.append((scope, destination, request))
        if self.on_write is not None:
            self.on_write()

        announce(report, ExportStage.WRITING, NOTHING_WRITTEN, ONE_FILE)
        if self.exception is not None:
            raise self.exception

        announce(report, ExportStage.WRITING, ONE_FILE, ONE_FILE)
        return ExportArtifact(paths=(destination,), truncation=self.truncation)


def build_instrument(name: str = "Lead") -> InstrumentExport:
    return InstrumentExport(
        name=name,
        channel=ChannelName.PULSE1,
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
        tuning=Tuning(),
    )


def build_sample(count: int = 2) -> SampleExport:
    return SampleExport(
        name="Kick",
        instruments=tuple(build_instrument(f"Kick {index}") for index in range(count)),
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


def build_project() -> ProjectExport:
    return ProjectExport(project=Project.create(title="Song"))


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

        result = outcome(results)
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.WAV
        assert result.filepath == filepath

    def test_success_calls_write_wave_with_correct_args(
        self,
        service,
        tmp_path,
    ) -> None:
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

        with patch(
            "sampletones_application.services.export.service.write_wave",
            side_effect=exception,
        ):
            export_service.export_wav(filepath, 44100, np.zeros(100))

        result = outcome(results)
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

        export_service.export_instrument(
            filepath,
            StubBackend(),
            build_instrument(),
        )

        result = outcome(results)
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.INSTRUMENT
        assert result.filepath == filepath

    def test_the_backend_receives_the_destination_and_the_request(
        self,
        service,
        tmp_path,
    ) -> None:
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

        result = outcome(results)
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
    def test_success_emits_export_success_with_the_destination(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        export_service.export_sample(tmp_path, StubBackend(), build_sample())

        result = outcome(results)
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.SAMPLE
        assert result.filepath == tmp_path

    def test_the_backend_receives_every_slice_in_one_call(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, _ = service
        backend = StubBackend()
        request = build_sample(3)

        export_service.export_sample(tmp_path, backend, request)

        assert backend.calls == [("sample", tmp_path, request)]

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        exception = OSError("no space")

        export_service.export_sample(
            tmp_path,
            StubBackend(exception=exception),
            build_sample(),
        )

        result = outcome(results)
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.SAMPLE
        assert result.exception is exception

    def test_a_sample_with_no_slices_emits_success(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        export_service.export_sample(tmp_path, StubBackend(), build_sample(0))

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.SAMPLE


class TestExportProject:
    def test_success_emits_export_success(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "song.ftm"

        export_service.export_project(filepath, StubBackend(), build_project())

        result = outcome(results)
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.PROJECT
        assert result.filepath == filepath

    def test_the_backend_receives_the_destination_and_the_request(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, _ = service
        filepath = tmp_path / "song.ftm"
        backend = StubBackend()
        request = build_project()

        export_service.export_project(filepath, backend, request)

        assert backend.calls == [("project", filepath, request)]

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        exception = OSError("no space")

        export_service.export_project(
            tmp_path / "song.ftm",
            StubBackend(exception=exception),
            build_project(),
        )

        result = outcome(results)
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.PROJECT
        assert result.exception is exception


class TestExportFormatReporting:
    def test_a_tracker_export_names_the_format_it_was_written_in(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        export_service.export_instrument(
            tmp_path / "inst.fti",
            StubBackend(),
            build_instrument(),
        )

        assert outcome(results).export_format == ExportFormat.FAMITRACKER

    def test_a_failed_tracker_export_names_the_format_it_was_written_in(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        export_service.export_sample(
            tmp_path,
            StubBackend(exception=OSError("fail")),
            build_sample(),
        )

        assert outcome(results).export_format == ExportFormat.FAMITRACKER

    def test_a_wav_export_names_no_format(self, service, tmp_path) -> None:
        export_service, results = service

        with patch("sampletones_application.services.export.service.write_wave"):
            export_service.export_wav(
                tmp_path / "track.wav",
                44100,
                np.zeros(100),
            )

        assert outcome(results).export_format is None


class TestExportTruncationReporting:
    def test_a_complete_instrument_reports_no_truncation(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        export_service.export_instrument(
            tmp_path / "inst.fti",
            StubBackend(),
            build_instrument(),
        )

        assert outcome(results).truncation is None

    def test_a_shortened_instrument_carries_the_backend_report(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service
        truncation = EnvelopeTruncation(
            frames=252,
            source_frames=300,
            instruments=1,
        )

        export_service.export_instrument(
            tmp_path / "inst.fti",
            StubBackend(truncation=truncation),
            build_instrument(),
        )

        assert outcome(results).truncation == truncation

    def test_a_shortened_sample_carries_the_backend_report(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service
        truncation = EnvelopeTruncation(
            frames=252,
            source_frames=410,
            instruments=2,
        )

        export_service.export_sample(
            tmp_path,
            StubBackend(truncation=truncation),
            build_sample(3),
        )

        assert outcome(results).truncation == truncation

    def test_a_wav_export_reports_no_truncation(
        self,
        service,
        tmp_path,
    ) -> None:
        export_service, results = service

        with patch("sampletones_application.services.export.service.write_wave"):
            export_service.export_wav(
                tmp_path / "track.wav",
                44100,
                np.zeros(100),
            )

        assert outcome(results).truncation is None


class TestExportServiceConcurrency:
    def test_second_export_while_first_running_is_rejected(
        self,
        tmp_path,
    ) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        with patch.object(
            export_service._executor,
            "execute",
            return_value=False,
        ):
            export_service.export_wav(
                tmp_path / "track.wav",
                44100,
                np.zeros(10),
            )

        assert results == []

    def test_multiple_simultaneous_calls_do_not_stack_up(
        self,
        tmp_path,
    ) -> None:
        export_service = ExportService()
        call_count = 0

        def on_result(result: Any) -> None:
            nonlocal call_count
            call_count += 1

        export_service.subscribe(on_result)

        with patch.object(
            export_service._executor,
            "execute",
            return_value=False,
        ):
            for _ in range(5):
                export_service.export_wav(
                    tmp_path / "track.wav",
                    44100,
                    np.zeros(10),
                )

        assert call_count == 0


class CancellingBackend:
    """Withdraws the run from inside it, the way a user pressing Cancel does."""

    def __init__(self, service: ExportService) -> None:
        self._service = service
        self.stages: List[ExportStage] = []

    @property
    def export_format(self) -> ExportFormat:
        return ExportFormat.NSF

    @property
    def supported_scopes(self) -> frozenset:
        return frozenset(ExportScope)

    def extension(self, scope: ExportScope) -> str:
        return ".nsf"

    def write_instrument(
        self,
        destination: Path,
        request: InstrumentExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        announce(report, ExportStage.WALKING, NOTHING_WRITTEN, None)
        self.stages.append(ExportStage.WALKING)
        self._service.cancel()
        announce(report, ExportStage.COMPRESSING, ONE_FILE, None)
        self.stages.append(ExportStage.COMPRESSING)
        return ExportArtifact(paths=(destination,), truncation=None)

    def write_sample(
        self,
        destination: Path,
        request: SampleExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        raise NotImplementedError

    def write_project(
        self,
        destination: Path,
        request: ProjectExport,
        report: ExportReporter = SILENT_REPORTER,
    ) -> ExportArtifact:
        raise NotImplementedError


class TestWhatARunSaysAboutItself:
    """The export speaks the vocabulary every other service speaks."""

    def test_a_run_opens_with_a_start(self, service, tmp_path) -> None:
        export_service, results = service
        export_service.export_instrument(tmp_path / "instrument.fti", StubBackend(), build_instrument())
        assert isinstance(results[0], ServiceStarted)

    def test_the_stage_a_format_names_reaches_the_subscriber(self, service, tmp_path) -> None:
        export_service, results = service
        export_service.export_instrument(tmp_path / "instrument.fti", StubBackend(), build_instrument())
        reported = [result for result in results if isinstance(result, ServiceProgress)]
        assert reported and all(result.current_item == ExportStage.WRITING for result in reported)

    def test_a_stage_that_lands_on_its_total_is_reported(self, service, tmp_path) -> None:
        export_service, results = service
        export_service.export_instrument(tmp_path / "instrument.fti", StubBackend(), build_instrument())
        reported = [result for result in results if isinstance(result, ServiceProgress)]
        assert reported[-1].completed == ONE_FILE


class TestWithdrawingARun:
    """A cancelled export answers with a cancellation rather than a failure."""

    def test_a_cancelled_run_ends_cancelled(self, service, tmp_path) -> None:
        export_service, results = service
        export_service.export_instrument(
            tmp_path / "instrument.nsf",
            CancellingBackend(export_service),
            build_instrument(),
        )
        assert isinstance(outcome(results), ServiceCancelled)

    def test_a_cancelled_run_reports_no_failure(self, service, tmp_path) -> None:
        export_service, results = service
        export_service.export_instrument(
            tmp_path / "instrument.nsf",
            CancellingBackend(export_service),
            build_instrument(),
        )
        assert not any(isinstance(result, (ExportSuccess, ExportError)) for result in results)

    def test_the_format_stops_where_it_was_told(self, service, tmp_path) -> None:
        export_service, _ = service
        backend = CancellingBackend(export_service)
        export_service.export_instrument(tmp_path / "instrument.nsf", backend, build_instrument())
        assert backend.stages == [ExportStage.WALKING]


class TestOneExportAtATime:
    """An export claims the application, so a second request is declined rather than queued."""

    def test_a_finished_run_leaves_the_service_idle(self, service, tmp_path) -> None:
        export_service, _ = service
        export_service.export_instrument(tmp_path / "instrument.fti", StubBackend(), build_instrument())
        assert export_service.is_running() is False

    def test_a_request_arriving_mid_run_is_declined(self, service, tmp_path) -> None:
        export_service, _ = service
        backend = StubBackend()
        second = StubBackend()

        def start_another() -> None:
            export_service.export_instrument(tmp_path / "second.fti", second, build_instrument())

        backend.on_write = start_another
        export_service.export_instrument(tmp_path / "instrument.fti", backend, build_instrument())
        assert second.calls == []
