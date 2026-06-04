from typing import Any, List

import numpy as np
import pytest

from sampletones_application.services.export import ExportError, ExportKind, ExportService, ExportSuccess
from sampletones_core.audio import read_wave


class TestExportWavIntegration:
    """ExportService.export_wav() with real write_wave and real filesystem."""

    def test_wav_file_is_created_on_disk(self, tmp_path, default_config) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "output.wav"
        export_service.export_wav(filepath, default_config.sample_rate, np.zeros(1000, dtype=np.float32))

        assert filepath.exists()

    def test_emits_export_success_with_correct_filepath(self, tmp_path, default_config) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "output.wav"
        export_service.export_wav(filepath, default_config.sample_rate, np.zeros(1000, dtype=np.float32))

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.WAV
        assert results[0].filepath == filepath

    def test_written_wav_is_readable(self, tmp_path, default_config) -> None:
        export_service = ExportService()
        export_service.subscribe(lambda _: None)

        filepath = tmp_path / "output.wav"
        export_service.export_wav(filepath, default_config.sample_rate, np.zeros(1000, dtype=np.float32))

        read_audio, read_sample_rate = read_wave(filepath)
        assert read_sample_rate == default_config.sample_rate
        assert read_audio.shape[0] > 0

    def test_invalid_sample_rate_emits_export_error(self, tmp_path) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_wav(tmp_path / "output.wav", 1234, np.zeros(100, dtype=np.float32))

        assert len(results) == 1
        assert isinstance(results[0], ExportError)
        assert results[0].kind == ExportKind.WAV


class TestExportInstrumentIntegration:
    """ExportService.export_instrument() with real Features.save() and real filesystem."""

    def test_fti_file_is_created_on_disk(self, tmp_path, pulse_features) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "instrument.fti"
        export_service.export_instrument(filepath, "test_instrument", pulse_features)

        assert filepath.exists()

    def test_emits_export_success_with_correct_kind_and_filepath(self, tmp_path, pulse_features) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "instrument.fti"
        export_service.export_instrument(filepath, "test_instrument", pulse_features)

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.INSTRUMENT
        assert results[0].filepath == filepath

    def test_directory_path_emits_export_error(self, tmp_path, pulse_features) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_instrument(tmp_path, "test_instrument", pulse_features)

        assert len(results) == 1
        assert isinstance(results[0], ExportError)
        assert results[0].kind == ExportKind.INSTRUMENT


class TestExportInstrumentsIntegration:
    """ExportService.export_instruments() with real Features.save() and real filesystem."""

    def test_all_fti_files_are_created_on_disk(self, tmp_path, pulse_features) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        exports = [
            (tmp_path / "inst_0.fti", "inst_0", pulse_features),
            (tmp_path / "inst_1.fti", "inst_1", pulse_features),
        ]
        export_service.export_instruments(tmp_path, exports)

        for filepath, _, _ in exports:
            assert filepath.exists()

    def test_emits_export_success_with_directory_filepath(self, tmp_path, pulse_features) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        exports = [(tmp_path / "inst.fti", "inst", pulse_features)]
        export_service.export_instruments(tmp_path, exports)

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.INSTRUMENTS
        assert results[0].filepath == tmp_path

    def test_new_directory_is_created(self, tmp_path, pulse_features) -> None:
        new_dir = tmp_path / "subdir"
        export_service = ExportService()
        export_service.subscribe(lambda _: None)

        export_service.export_instruments(new_dir, [(new_dir / "inst.fti", "inst", pulse_features)])

        assert new_dir.exists()

    def test_empty_exports_list_creates_no_files(self, tmp_path) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_instruments(tmp_path, [])

        fti_files = list(tmp_path.glob("*.fti"))
        assert fti_files == []
        assert isinstance(results[0], ExportSuccess)
