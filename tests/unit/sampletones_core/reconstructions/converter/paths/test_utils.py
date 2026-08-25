from pathlib import Path
from typing import List

import pytest

from sampletones_core.configs import Config
from sampletones_core.reconstructions.converter.paths import (
    filter_files,
    get_audio_files,
    get_output_path,
    get_relative_path,
    group_output_path,
    top_level_audio_files,
)
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION


@pytest.fixture(scope="module")
def config() -> Config:
    return Config()


class TestGetRelativePath:
    def test_preserves_subdirectory_structure(self, tmp_path: Path) -> None:
        base = tmp_path / "base"
        audio_file = base / "sub" / "file.wav"
        output = tmp_path / "output"
        result = get_relative_path(base, audio_file, output)
        assert result == output / "sub" / "file.stn"

    def test_replaces_extension_with_suffix(self, tmp_path: Path) -> None:
        base = tmp_path / "base"
        audio_file = base / "song.wav"
        output = tmp_path / "output"
        result = get_relative_path(base, audio_file, output)
        assert result.suffix == EXT_FILE_RECONSTRUCTION

    def test_result_is_absolute(self) -> None:
        base = Path("base")
        audio_file = Path("base/song.wav")
        output = Path("output")
        result = get_relative_path(base, audio_file, output)
        assert result.is_absolute()


class TestGetOutputPath:
    def test_file_input_returns_path_with_reconstruction_extension(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        result = get_output_path(config, audio_file)
        assert result.suffix == EXT_FILE_RECONSTRUCTION

    def test_directory_input_returns_path_ending_with_directory_name(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        result = get_output_path(config, tmp_path)
        assert result.name == tmp_path.name

    def test_non_existent_input_raises_file_not_found_error(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            get_output_path(config, missing)


class TestGetAudioFiles:
    def test_finds_wav_files_in_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        result = get_audio_files(tmp_path)
        assert len(result) == 2

    def test_ignores_non_audio_files(self, tmp_path: Path) -> None:
        (tmp_path / "audio.wav").touch()
        (tmp_path / "notes.txt").touch()
        result = get_audio_files(tmp_path)
        assert len(result) == 1

    def test_searches_recursively(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "deep.wav").touch()
        result = get_audio_files(tmp_path)
        assert len(result) == 1
        assert result[0] == subdir / "deep.wav"

    def test_sorted_when_sort_is_true(self, tmp_path: Path) -> None:
        (tmp_path / "c.wav").touch()
        (tmp_path / "a.wav").touch()
        (tmp_path / "b.wav").touch()
        result = get_audio_files(tmp_path, sort=True)
        names = [path.name for path in result]
        assert names == sorted(names)


class TestFilterFiles:
    def test_includes_files_without_existing_output(self, tmp_path: Path) -> None:
        audio_files: List[Path] = [tmp_path / "song.wav"]
        output_directory = tmp_path / "output"
        result = filter_files(audio_files, tmp_path, output_directory)
        assert result == audio_files

    def test_excludes_files_with_existing_output(self, tmp_path: Path) -> None:
        audio_file = tmp_path / "song.wav"
        output_directory = tmp_path / "output"
        output_file = get_relative_path(tmp_path, audio_file, output_directory)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.touch()
        result = filter_files([audio_file], tmp_path, output_directory)
        assert result == []


class TestTopLevelAudioFiles:
    """Gathering the sources of one reconstruction stays with the folder that was pointed at."""

    def test_reports_the_audio_files_the_folder_itself_holds(self, tmp_path: Path) -> None:
        (tmp_path / "b.wav").touch()
        (tmp_path / "a.wav").touch()
        (tmp_path / "notes.txt").write_text("not audio")

        assert [path.name for path in top_level_audio_files(tmp_path)] == ["a.wav", "b.wav"]

    def test_a_nested_recording_stays_where_it_is(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "deep.wav").touch()
        (tmp_path / "a.wav").touch()

        assert [path.name for path in top_level_audio_files(tmp_path)] == ["a.wav"]

    def test_a_folder_of_nothing_reports_nothing(self, tmp_path: Path) -> None:
        assert top_level_audio_files(tmp_path) == []
