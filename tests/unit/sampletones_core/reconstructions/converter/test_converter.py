from pathlib import Path
from unittest.mock import patch

import pytest

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter import (
    ReconstructionConverter,
    reconstruct_file,
)
from sampletones_shared.exceptions import NoFilesToProcessError

_RECONSTRUCTOR_PATCH = "sampletones_core.reconstructions.converter.converter.Reconstructor"


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


class TestReconstructionConverterInit:
    def test_stores_config_as_copy(self, config: Config, tmp_path: Path) -> None:
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        assert converter.config is not config

    def test_stores_input_path(self, config: Config, tmp_path: Path) -> None:
        input_path = tmp_path / "song.wav"
        converter = ReconstructionConverter(config, input_path, is_file=True)
        assert converter.input_path == input_path

    def test_is_file_flag_stored(self, config: Config, tmp_path: Path) -> None:
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        assert converter.is_file is True

    def test_tracking_variables_initialized_to_zero(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        assert converter.total_files == 0
        assert converter.completed_files == 0


class TestReconstructionConverterStart:
    def test_already_running_does_not_spawn_thread(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        converter.running = True
        converter.start()
        assert converter.monitor_thread is None


class TestReconstructionConverterCreateTasks:
    def test_file_input_returns_single_task(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        converter = ReconstructionConverter(config, audio_file, is_file=True)
        with patch(_RECONSTRUCTOR_PATCH):
            result = converter._create_tasks()
        assert len(result) == 1

    def test_file_task_uses_input_path_as_source(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        converter = ReconstructionConverter(config, audio_file, is_file=True)
        with patch(_RECONSTRUCTOR_PATCH):
            result = converter._create_tasks()
        assert result[0][1] == audio_file

    def test_directory_input_returns_one_task_per_audio_file(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        with patch(_RECONSTRUCTOR_PATCH):
            result = converter._create_tasks()
        assert len(result) == 2

    def test_directory_with_no_audio_files_raises_no_files_to_process_error(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        with patch(_RECONSTRUCTOR_PATCH):
            with pytest.raises(NoFilesToProcessError):
                converter._create_tasks()


class TestReconstructionConverterGetTaskFunction:
    def test_returns_reconstruct_file_function(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        assert converter._get_task_function() is reconstruct_file


class TestReconstructionConverterProcessResults:
    def test_file_mode_returns_first_result(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        path_a = tmp_path / "a.stn"
        path_b = tmp_path / "b.stn"
        converter = ReconstructionConverter(
            config,
            tmp_path / "song.wav",
            is_file=True,
        )
        assert converter._process_results([path_a, path_b]) == path_a

    def test_directory_mode_returns_input_path(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        assert converter._process_results([tmp_path / "a.stn"]) == tmp_path


class TestReconstructionConverterNotifyProgress:
    def test_total_files_updated_from_total_tasks(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        converter.total_tasks = 5
        converter._notify_progress()
        assert converter.total_files == 5

    def test_completed_files_updated_from_completed_tasks(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        converter.total_tasks = 3
        converter.completed_tasks = 3
        converter.audio_files = [
            tmp_path / "a.wav",
            tmp_path / "b.wav",
            tmp_path / "c.wav",
        ]
        converter._notify_progress()
        assert converter.completed_files == 3

    def test_current_file_set_after_first_completion(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        path_a = tmp_path / "a.wav"
        path_b = tmp_path / "b.wav"
        converter = ReconstructionConverter(config, tmp_path, is_file=False)
        converter.audio_files = [path_a, path_b]
        converter.total_tasks = 2
        converter.completed_tasks = 1
        converter._notify_progress()
        assert converter.current_file == str(path_a)
        converter._notify_progress()
        assert converter.current_file == str(path_a)
