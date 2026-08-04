from typing import Any, Final, List

import numpy as np
import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_core.audio import read_wave
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.trackers.implementation.famitracker import FamiTrackerBackend
from sampletones_core.trackers.request import InstrumentExport, SampleExport

NES_FREQUENCY: Final[int] = 60


@pytest.fixture(name="backend")
def backend_fixture() -> FamiTrackerBackend:
    return FamiTrackerBackend()


def instrument_export(name: str, features: Features) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        generator=GeneratorName.PULSE1,
        features=features,
        loop=False,
        nes_frequency=NES_FREQUENCY,
    )


def sample_export(name: str, *instruments: InstrumentExport) -> SampleExport:
    return SampleExport(name=name, instruments=instruments, nes_frequency=NES_FREQUENCY)


class TestExportWavIntegration:
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
    def test_fti_file_is_created_on_disk(self, tmp_path, pulse_features, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "instrument.fti"
        export_service.export_instrument(filepath, backend, instrument_export("test_instrument", pulse_features))

        assert filepath.exists()

    def test_emits_export_success_with_correct_kind_and_filepath(self, tmp_path, pulse_features, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "instrument.fti"
        export_service.export_instrument(filepath, backend, instrument_export("test_instrument", pulse_features))

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.INSTRUMENT
        assert results[0].filepath == filepath

    def test_directory_path_emits_export_error(self, tmp_path, pulse_features, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_instrument(tmp_path, backend, instrument_export("test_instrument", pulse_features))

        assert len(results) == 1
        assert isinstance(results[0], ExportError)
        assert results[0].kind == ExportKind.INSTRUMENT


class TestExportSampleIntegration:
    def test_all_fti_files_are_created_on_disk(self, tmp_path, pulse_features, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        request = sample_export(
            "sample",
            instrument_export("inst_0", pulse_features),
            instrument_export("inst_1", pulse_features),
        )
        export_service.export_sample(tmp_path / "sample.fti", backend, request)

        assert (tmp_path / "inst_0.fti").exists()
        assert (tmp_path / "inst_1.fti").exists()

    def test_emits_export_success_with_a_path_that_was_written(self, tmp_path, pulse_features, backend) -> None:
        """A batch names its slices after the destination, so the result reports one of the
        slices it wrote and the dialog announcing it opens a file that is there.
        """
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        request = sample_export("sample", instrument_export("inst", pulse_features))
        export_service.export_sample(tmp_path / "sample.fti", backend, request)

        assert len(results) == 1
        assert isinstance(results[0], ExportSuccess)
        assert results[0].kind == ExportKind.SAMPLE
        assert results[0].filepath == tmp_path / "inst.fti"
        assert results[0].filepath.exists()

    def test_new_directory_is_created(self, tmp_path, pulse_features, backend) -> None:
        new_dir = tmp_path / "subdir"
        export_service = ExportService()
        export_service.subscribe(lambda _: None)

        request = sample_export("sample", instrument_export("inst", pulse_features))
        export_service.export_sample(new_dir / "sample.fti", backend, request)

        assert new_dir.exists()

    def test_a_sample_with_no_slices_creates_no_files(self, tmp_path, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_sample(tmp_path / "sample.fti", backend, sample_export("sample"))

        assert list(tmp_path.glob("*.fti")) == []
        assert isinstance(results[0], ExportSuccess)
