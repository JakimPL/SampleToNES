from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.trackers.format import TrackerFormat


class TestExportSuccess:
    def test_stores_kind_and_filepath(self) -> None:
        filepath = Path("/exports/track.wav")
        success = ExportSuccess(
            kind=ExportKind.WAV,
            filepath=filepath,
            tracker_format=None,
            truncation=None,
        )
        assert success.kind == ExportKind.WAV
        assert success.filepath == filepath
        assert success.tracker_format is None
        assert success.truncation is None

    def test_stores_the_tracker_format(self) -> None:
        success = ExportSuccess(
            kind=ExportKind.INSTRUMENT,
            filepath=Path("/x"),
            tracker_format=TrackerFormat.BITPHASE,
            truncation=None,
        )
        assert success.tracker_format == TrackerFormat.BITPHASE

    def test_stores_the_truncation(self) -> None:
        truncation = EnvelopeTruncation(
            frames=252,
            source_frames=300,
            instruments=1,
        )
        success = ExportSuccess(
            kind=ExportKind.INSTRUMENT,
            filepath=Path("/x"),
            tracker_format=TrackerFormat.FAMITRACKER,
            truncation=truncation,
        )
        assert success.truncation == truncation

    def test_frozen(self) -> None:
        success = ExportSuccess(
            kind=ExportKind.WAV,
            filepath=Path("/x"),
            tracker_format=None,
            truncation=None,
        )
        with pytest.raises(FrozenInstanceError):
            success.kind = ExportKind.INSTRUMENT  # type: ignore[misc]

    def test_equality(self) -> None:
        path = Path("/x")
        assert ExportSuccess(
            kind=ExportKind.WAV,
            filepath=path,
            tracker_format=None,
            truncation=None,
        ) == ExportSuccess(
            kind=ExportKind.WAV,
            filepath=path,
            tracker_format=None,
            truncation=None,
        )
        assert ExportSuccess(
            kind=ExportKind.WAV,
            filepath=path,
            tracker_format=None,
            truncation=None,
        ) != ExportSuccess(
            kind=ExportKind.INSTRUMENT,
            filepath=path,
            tracker_format=None,
            truncation=None,
        )

    def test_the_tracker_format_separates_two_otherwise_equal_results(self) -> None:
        path = Path("/x")
        assert ExportSuccess(
            kind=ExportKind.INSTRUMENT,
            filepath=path,
            tracker_format=TrackerFormat.FAMITRACKER,
            truncation=None,
        ) != ExportSuccess(
            kind=ExportKind.INSTRUMENT,
            filepath=path,
            tracker_format=TrackerFormat.BITPHASE,
            truncation=None,
        )


class TestExportError:
    def test_stores_kind_and_exception(self) -> None:
        exception = OSError("disk full")
        error = ExportError(
            kind=ExportKind.INSTRUMENT,
            tracker_format=TrackerFormat.FAMITRACKER,
            exception=exception,
        )
        assert error.kind == ExportKind.INSTRUMENT
        assert error.tracker_format == TrackerFormat.FAMITRACKER
        assert error.exception is exception

    def test_frozen(self) -> None:
        error = ExportError(
            kind=ExportKind.WAV,
            tracker_format=None,
            exception=OSError(),
        )
        with pytest.raises(FrozenInstanceError):
            error.kind = ExportKind.SAMPLE  # type: ignore[misc]

    def test_eq_false_same_exception_instances_differ(self) -> None:
        exception = OSError("same")
        error_a = ExportError(
            kind=ExportKind.WAV,
            tracker_format=None,
            exception=exception,
        )
        error_b = ExportError(
            kind=ExportKind.WAV,
            tracker_format=None,
            exception=exception,
        )
        assert error_a != error_b

    def test_same_instance_equals_itself(self) -> None:
        error = ExportError(
            kind=ExportKind.WAV,
            tracker_format=None,
            exception=OSError(),
        )
        assert error == error  # noqa: PLR0124
