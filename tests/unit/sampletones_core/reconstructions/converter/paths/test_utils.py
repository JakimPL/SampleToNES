import errno
from pathlib import Path
from typing import List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName
from sampletones_core.reconstructions.converter.paths import (
    ConfigDirectoryFields,
    filter_files,
    get_audio_files,
    get_output_path,
    get_relative_path,
    group_output_path,
    reconstructions_directory,
    walk_entries,
)
from sampletones_core.reconstructions.converter.paths.utils import ConfigDirectories
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from tests.suite.files import LOCKED_FOLDER, NAMES_ONLY_FOLDER, held_at, requires_folder_permissions

CHANNELS = frozenset(DEFAULT_CHANNELS)


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


class TestConfigDirectories:
    """A configuration names one directory per channel set under its reconstructions directory, as
    its own fields name it."""

    def test_each_channel_set_names_its_own_directory(self, config: Config) -> None:
        directories = ConfigDirectories(config)
        channel_sets = (CHANNELS, frozenset({ChannelName.PULSE1}), CHANNELS)

        assert [directories.directory(channels) for channels in channel_sets] == [
            reconstructions_directory(config) / ConfigDirectoryFields.from_config(config, channels).directory_name
            for channels in channel_sets
        ]


class TestGetOutputPath:
    def test_file_input_returns_path_with_reconstruction_extension(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        audio_file = tmp_path / "song.wav"
        audio_file.touch()
        result = get_output_path(config, audio_file, CHANNELS)
        assert result.suffix == EXT_FILE_RECONSTRUCTION

    def test_directory_input_returns_path_ending_with_directory_name(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        result = get_output_path(config, tmp_path, CHANNELS)
        assert result.name == tmp_path.name

    def test_non_existent_input_raises_file_not_found_error(
        self,
        config: Config,
        tmp_path: Path,
    ) -> None:
        missing = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            get_output_path(config, missing, CHANNELS)


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


@requires_folder_permissions
class TestWalkEntries:
    """A walk reads every folder it may open and passes over the ones it may not."""

    def test_a_locked_folder_is_passed_over_with_what_it_holds(self, tmp_path: Path) -> None:
        (tmp_path / "open").mkdir()
        (tmp_path / "open" / "kept.wav").touch()
        locked = tmp_path / "locked"
        (locked / "deeper").mkdir(parents=True)
        (locked / "hidden.wav").touch()

        with held_at(locked, LOCKED_FOLDER):
            names = sorted(path.name for path in walk_entries(tmp_path))

        assert names == ["kept.wav", "locked", "open"]

    def test_a_folder_that_cannot_be_opened_raises(self, tmp_path: Path) -> None:
        (tmp_path / "take.wav").touch()

        with held_at(tmp_path, LOCKED_FOLDER), pytest.raises(PermissionError):
            walk_entries(tmp_path)

    def test_a_folder_listing_names_only_raises_naming_itself(self, tmp_path: Path) -> None:
        """A folder may list its names and keep its recordings closed, which leaves the walk nothing
        to read, as a folder that cannot be opened does."""
        root = tmp_path / "names_only"
        root.mkdir()
        (root / "take.wav").touch()

        with held_at(root, NAMES_ONLY_FOLDER), pytest.raises(PermissionError) as raised:
            walk_entries(root)

        assert (raised.value.errno, raised.value.filename) == (errno.EACCES, str(root))


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
