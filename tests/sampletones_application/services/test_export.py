from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from sampletones_application.services.export import ExportError, ExportKind, ExportService, ExportSuccess


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

        with patch("sampletones_application.services.export.write_wave"):
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

        with patch("sampletones_application.services.export.write_wave") as mock_write:
            export_service.export_wav(filepath, 44100, audio)

        mock_write.assert_called_once_with(filepath, 44100, audio)

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "track.wav"
        exception = OSError("disk full")

        with patch("sampletones_application.services.export.write_wave", side_effect=exception):
            export_service.export_wav(filepath, 44100, np.zeros(100))

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.WAV
        assert result.exception is exception

    def test_error_does_not_emit_success(self, service, tmp_path) -> None:
        export_service, results = service

        with patch(
            "sampletones_application.services.export.write_wave",
            side_effect=RuntimeError("fail"),
        ):
            export_service.export_wav(tmp_path / "x.wav", 44100, np.zeros(10))

        assert not any(isinstance(r, ExportSuccess) for r in results)


class TestExportInstrument:
    def test_success_emits_export_success(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "instrument.fti"
        feature = MagicMock()

        export_service.export_instrument(filepath, "guitar", feature)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.INSTRUMENT
        assert result.filepath == filepath

    def test_success_calls_feature_save(self, service, tmp_path) -> None:
        export_service, _ = service
        filepath = tmp_path / "instrument.fti"
        feature = MagicMock()

        export_service.export_instrument(filepath, "guitar", feature)

        feature.save.assert_called_once_with(filepath, "guitar")

    def test_error_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        filepath = tmp_path / "instrument.fti"
        exception = PermissionError("read-only")
        feature = MagicMock()
        feature.save.side_effect = exception

        export_service.export_instrument(filepath, "bass", feature)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.INSTRUMENT
        assert result.exception is exception

    def test_error_does_not_emit_success(self, service, tmp_path) -> None:
        export_service, results = service
        feature = MagicMock()
        feature.save.side_effect = OSError("fail")

        export_service.export_instrument(tmp_path / "x.fti", "piano", feature)

        assert not any(isinstance(r, ExportSuccess) for r in results)


class TestExportInstruments:
    def test_success_calls_save_for_each_export(self, service, tmp_path) -> None:
        export_service, _ = service
        features = [MagicMock(), MagicMock(), MagicMock()]
        exports = [(tmp_path / f"inst_{i}.fti", f"inst_{i}", features[i]) for i in range(3)]

        export_service.export_instruments(tmp_path, exports)

        for feature in features:
            feature.save.assert_called_once()

    def test_success_emits_export_success_with_directory(self, service, tmp_path) -> None:
        export_service, results = service
        feature = MagicMock()
        exports = [(tmp_path / "inst.fti", "inst", feature)]

        export_service.export_instruments(tmp_path, exports)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportSuccess)
        assert result.kind == ExportKind.INSTRUMENTS
        assert result.filepath == tmp_path

    def test_success_creates_directory(self, service, tmp_path) -> None:
        export_service, _ = service
        new_dir = tmp_path / "subdir"
        feature = MagicMock()
        exports = [(new_dir / "inst.fti", "inst", feature)]

        export_service.export_instruments(new_dir, exports)

        assert new_dir.exists()

    def test_error_on_first_save_emits_export_error(self, service, tmp_path) -> None:
        export_service, results = service
        exception = OSError("no space")
        first_feature = MagicMock()
        first_feature.save.side_effect = exception
        second_feature = MagicMock()
        exports = [
            (tmp_path / "first.fti", "first", first_feature),
            (tmp_path / "second.fti", "second", second_feature),
        ]

        export_service.export_instruments(tmp_path, exports)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ExportError)
        assert result.kind == ExportKind.INSTRUMENTS
        assert result.exception is exception

    def test_error_stops_after_first_failure(self, service, tmp_path) -> None:
        export_service, _ = service
        first_feature = MagicMock()
        first_feature.save.side_effect = OSError("fail")
        second_feature = MagicMock()
        exports = [
            (tmp_path / "first.fti", "first", first_feature),
            (tmp_path / "second.fti", "second", second_feature),
        ]

        export_service.export_instruments(tmp_path, exports)

        second_feature.save.assert_not_called()

    def test_empty_exports_list_emits_success(self, service, tmp_path) -> None:
        export_service, results = service

        export_service.export_instruments(tmp_path, [])

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.INSTRUMENTS


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
