from typing import Any, Final, List

import numpy as np
import pytest

from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.result import ServiceProgress
from sampletones_core.audio import read_wave
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.exports.implementation.famitracker import FamiTrackerBackend
from sampletones_core.exports.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.exports.stage import ExportStage
from sampletones_core.project.project import Project
from sampletones_core.timing import SongTiming
from sampletones_player.export import NSFBackend
from sampletones_player.specification.nsf import NSF_MAGIC, PROGRAM_SIZE
from sampletones_shared.music import Tuning
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_sample,
)
from tests.suite.player import varied_features

NES_FREQUENCY: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60
ROWS_PER_PATTERN: Final[int] = 4
SOUNDING_TICKS: Final[int] = 8


def outcome(results: List[Any]) -> Any:
    """The result a run finished on, which follows whatever it said while it ran."""
    return results[-1]


@pytest.fixture(name="backend")
def backend_fixture() -> FamiTrackerBackend:
    return FamiTrackerBackend()


@pytest.fixture(name="console_backend")
def console_backend_fixture() -> NSFBackend:
    return NSFBackend()


def overlong_features(initial_pitch: int) -> Features:
    """Envelopes turning over at every tick for longer than the program area has room for."""
    return varied_features(PROGRAM_SIZE, initial_pitch, duty_cycle=True)


def instrument_export(name: str, features: Features) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        channel=ChannelName.PULSE1,
        features=features,
        loop=False,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


def sample_export(name: str, *instruments: InstrumentExport) -> SampleExport:
    return SampleExport(
        name=name,
        instruments=instruments,
        nes_frequency=NES_FREQUENCY,
        tuning=Tuning(),
    )


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

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.WAV
        assert outcome(results).filepath == filepath

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

        assert isinstance(outcome(results), ExportError)
        assert outcome(results).kind == ExportKind.WAV


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

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.INSTRUMENT
        assert outcome(results).filepath == filepath

    def test_directory_path_emits_export_error(self, tmp_path, pulse_features, backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_instrument(tmp_path, backend, instrument_export("test_instrument", pulse_features))

        assert isinstance(outcome(results), ExportError)
        assert outcome(results).kind == ExportKind.INSTRUMENT


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

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.SAMPLE
        assert outcome(results).filepath == tmp_path / "inst.fti"
        assert outcome(results).filepath.exists()

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
        assert isinstance(outcome(results), ExportSuccess)


class TestExportToTheConsoleIntegration:
    """The console player's backend writing through the same service the trackers do."""

    def test_a_playable_program_is_created_on_disk(self, tmp_path, pulse_features, console_backend) -> None:
        export_service = ExportService()
        export_service.subscribe(lambda _: None)

        filepath = tmp_path / "sample.nsf"
        export_service.export_sample(
            filepath, console_backend, sample_export("sample", instrument_export("inst", pulse_features))
        )

        assert filepath.read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC

    def test_the_result_names_the_program_that_was_written(self, tmp_path, pulse_features, console_backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "sample.nsf"
        export_service.export_sample(
            filepath, console_backend, sample_export("sample", instrument_export("inst", pulse_features))
        )

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.SAMPLE
        assert outcome(results).filepath == filepath

    def test_a_reconstruction_outgrowing_the_program_area_is_reported(self, tmp_path, console_backend) -> None:
        """The console holds one program in 32 KB, so a reconstruction running past it reaches
        the user as a failed export rather than as a file playing part of itself.
        """
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "sample.nsf"
        request = sample_export("sample", instrument_export("inst", overlong_features(REFERENCE_PITCH)))
        export_service.export_sample(filepath, console_backend, request)

        assert isinstance(outcome(results), ExportError)
        assert outcome(results).kind == ExportKind.SAMPLE


def arranged_project() -> Project:
    """A project whose song sounds one sample from its first row."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(pitch=REFERENCE_PITCH, count=SOUNDING_TICKS),
        rows_per_pattern=ROWS_PER_PATTERN,
    )
    place_instrument(
        project,
        channel_name=ChannelName.PULSE1,
        row_index=0,
        sample=sample,
    )
    return project


class TestExportProjectToTheConsoleIntegration:
    """A whole arrangement reaching the console through the service the application exports by."""

    def test_the_song_is_written_as_one_program(self, tmp_path, console_backend) -> None:
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        filepath = tmp_path / "song.nsf"
        export_service.export_project(filepath, console_backend, ProjectExport(project=arranged_project()))

        assert isinstance(outcome(results), ExportSuccess)
        assert outcome(results).kind == ExportKind.PROJECT
        assert outcome(results).filepath == filepath
        assert filepath.read_bytes()[: len(NSF_MAGIC)] == NSF_MAGIC

    def test_the_walk_reads_as_a_fraction_of_the_song(self, tmp_path, console_backend) -> None:
        """A song states the ticks it lasts before a row of it is played, so the stage that
        plays it out travels toward a length the dialog can draw."""
        project = arranged_project()
        export_service = ExportService()
        results: List[Any] = []
        export_service.subscribe(results.append)

        export_service.export_project(tmp_path / "song.nsf", console_backend, ProjectExport(project=project))

        walked = [
            result
            for result in results
            if isinstance(result, ServiceProgress) and result.current_item == ExportStage.WALKING
        ]
        groove = SongTiming.from_project(project).groove()
        assert walked
        assert walked[-1].total == project.song.order_length() * groove.total_ticks
