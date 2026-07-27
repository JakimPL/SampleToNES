from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.export.truncation import ExportTruncation


class TestExportSuccess:
    def test_stores_kind_and_filepath(self) -> None:
        filepath = Path("/exports/track.wav")
        success = ExportSuccess(kind=ExportKind.WAV, filepath=filepath, truncation=None)
        assert success.kind == ExportKind.WAV
        assert success.filepath == filepath
        assert success.truncation is None

    def test_stores_the_truncation(self) -> None:
        truncation = ExportTruncation(frames=252, source_frames=300, instruments=1)
        success = ExportSuccess(kind=ExportKind.INSTRUMENT, filepath=Path("/x"), truncation=truncation)
        assert success.truncation == truncation

    def test_frozen(self) -> None:
        success = ExportSuccess(kind=ExportKind.WAV, filepath=Path("/x"), truncation=None)
        with pytest.raises(FrozenInstanceError):
            success.kind = ExportKind.INSTRUMENT  # type: ignore[misc]

    def test_equality(self) -> None:
        path = Path("/x")
        assert ExportSuccess(kind=ExportKind.WAV, filepath=path, truncation=None) == ExportSuccess(
            kind=ExportKind.WAV, filepath=path, truncation=None
        )
        assert ExportSuccess(kind=ExportKind.WAV, filepath=path, truncation=None) != ExportSuccess(
            kind=ExportKind.INSTRUMENT, filepath=path, truncation=None
        )


class TestExportError:
    def test_stores_kind_and_exception(self) -> None:
        exception = OSError("disk full")
        error = ExportError(kind=ExportKind.INSTRUMENT, exception=exception)
        assert error.kind == ExportKind.INSTRUMENT
        assert error.exception is exception

    def test_frozen(self) -> None:
        error = ExportError(kind=ExportKind.WAV, exception=OSError())
        with pytest.raises(FrozenInstanceError):
            error.kind = ExportKind.INSTRUMENTS  # type: ignore[misc]

    def test_eq_false_same_exception_instances_differ(self) -> None:
        exception = OSError("same")
        error_a = ExportError(kind=ExportKind.WAV, exception=exception)
        error_b = ExportError(kind=ExportKind.WAV, exception=exception)
        assert error_a != error_b

    def test_same_instance_equals_itself(self) -> None:
        error = ExportError(kind=ExportKind.WAV, exception=OSError())
        assert error == error  # noqa: PLR0124
