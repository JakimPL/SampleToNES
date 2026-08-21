from pathlib import Path
from unittest.mock import patch

import pytest

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter import (
    DirectoryConversion,
    GroupConversion,
    ReconstructionConverter,
    reconstruct_job,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.exceptions import NoFilesToProcessError

_RECONSTRUCTOR_PATCH = "sampletones_core.reconstructions.converter.converter.Reconstructor"


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


@pytest.fixture(scope="module")
def stems(config: Config) -> StemsConfig:
    return StemsConfig.single_entry(list(config.generation.channels))


def _group(path: Path, stems: StemsConfig) -> GroupConversion:
    return GroupConversion(sources=(path,), stems=stems)


class TestReconstructionConverterInit:
    def test_stores_config_as_copy(self, config: Config, stems: StemsConfig, tmp_path: Path) -> None:
        converter = ReconstructionConverter(config, _group(tmp_path / "song.wav", stems))
        assert converter.config is not config

    def test_stores_the_plan_it_runs(self, config: Config, stems: StemsConfig, tmp_path: Path) -> None:
        plan = _group(tmp_path / "song.wav", stems)
        converter = ReconstructionConverter(config, plan)
        assert converter.plan is plan


class TestReconstructionConverterStart:
    def test_already_running_does_not_spawn_thread(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, _group(tmp_path / "song.wav", stems))
        converter.running = True
        converter.start()
        assert converter.monitor_thread is None


class TestReconstructionConverterCreateTasks:
    def test_a_group_plan_returns_a_single_task(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        converter = ReconstructionConverter(config, _group(audio_file, stems))
        with patch(_RECONSTRUCTOR_PATCH):
            tasks = converter._create_tasks()
        assert len(tasks) == 1

    def test_each_task_carries_its_job(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        converter = ReconstructionConverter(config, _group(audio_file, stems))
        with patch(_RECONSTRUCTOR_PATCH):
            tasks = converter._create_tasks()
        assert tasks[0][1] is converter.jobs[0]
        assert converter.jobs[0].sources == (audio_file,)

    def test_a_directory_plan_returns_one_task_per_audio_file(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        converter = ReconstructionConverter(config, DirectoryConversion(directory=tmp_path, stems=stems))
        with patch(_RECONSTRUCTOR_PATCH):
            tasks = converter._create_tasks()
        assert len(tasks) == 2

    def test_a_directory_with_no_audio_files_raises_no_files_to_process_error(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, DirectoryConversion(directory=tmp_path, stems=stems))
        with patch(_RECONSTRUCTOR_PATCH):
            with pytest.raises(NoFilesToProcessError):
                converter._create_tasks()


class TestReconstructionConverterGetTaskFunction:
    def test_returns_the_job_conversion_function(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, _group(tmp_path / "song.wav", stems))
        assert converter._get_task_function() is reconstruct_job


class TestReconstructionConverterProcessResults:
    def test_reports_the_reconstructions_that_were_written(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        written = tmp_path / "a.stn"
        written.touch()
        converter = ReconstructionConverter(config, _group(tmp_path / "song.wav", stems))
        assert converter._process_results([written]) == (written,)

    def test_leaves_out_a_job_that_wrote_nothing(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        """A source the loader has no reader for names its output and writes none, so the run
        reports only what a reader can open."""
        written = tmp_path / "a.stn"
        written.touch()
        converter = ReconstructionConverter(config, _group(tmp_path / "song.wav", stems))
        assert converter._process_results([written, tmp_path / "missing.stn"]) == (written,)


class TestReconstructionConverterNotifyProgress:
    def test_current_file_names_the_job_that_completed(
        self,
        config: Config,
        stems: StemsConfig,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        converter = ReconstructionConverter(config, DirectoryConversion(directory=tmp_path, stems=stems))
        with patch(_RECONSTRUCTOR_PATCH):
            converter._create_tasks()

        converter.total_tasks = len(converter.jobs)
        converter.completed_tasks = 1
        converter._notify_progress()
        assert converter.current_file == str(converter.jobs[0].sources[0])
