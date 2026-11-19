from pathlib import Path
from typing import Callable

import pytest

from sampletones_shared.paths.extensions import FILE_KINDS, FileKind, file_kind, is_audio_file
from tests.suite.files import NAMES_ONLY_FOLDER, held_at, requires_folder_permissions


class TestIsAudioFile:
    """A recording is a file with a recording's extension that the reader may inspect."""

    def test_a_recording_reads_as_one(self, tmp_path: Path) -> None:
        recording = tmp_path / "take.WAV"
        recording.touch()

        assert is_audio_file(recording)

    def test_another_kind_of_file_reads_as_none(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.touch()

        assert not is_audio_file(notes)

    def test_a_folder_named_like_a_recording_reads_as_none(self, tmp_path: Path) -> None:
        folder = tmp_path / "takes.wav"
        folder.mkdir()

        assert not is_audio_file(folder)

    @requires_folder_permissions
    def test_a_recording_in_a_folder_listing_names_only_reads_as_none(self, tmp_path: Path) -> None:
        folder = tmp_path / "names_only"
        folder.mkdir()
        (folder / "take.wav").touch()

        with held_at(folder, NAMES_ONLY_FOLDER):
            assert not is_audio_file(folder / "take.wav")


class TestAFilesKindIsReadFromItsExtensionInAnyCase:
    """A file reads as one kind on every surface however its extension is cased, since file systems
    on Windows and macOS hand names over as the user typed them."""

    @pytest.mark.parametrize("extension, kind", FILE_KINDS.items())
    @pytest.mark.parametrize("spelling", (str.lower, str.upper, str.title), ids=("lower", "upper", "title"))
    def test_each_spelling_names_the_kind(self, extension: str, kind: FileKind, spelling: Callable[[str], str]) -> None:
        assert file_kind(Path(f"take{spelling(extension)}")) is kind

    @pytest.mark.parametrize(
        "name",
        ("notes.txt", "take", "take.", ".stn", "take.stn.bak", "take.wav.txt", "take.st"),
    )
    def test_a_name_without_a_known_extension_names_no_kind(self, name: str) -> None:
        assert file_kind(Path(name)) is None

    def test_the_kind_comes_from_the_last_extension(self) -> None:
        assert file_kind(Path("take.wav.stn")) is FileKind.RECONSTRUCTION

    def test_a_dotted_folder_name_reads_by_its_extension_alone(self, tmp_path: Path) -> None:
        folder = tmp_path / "takes.stn"
        folder.mkdir()

        assert file_kind(folder) is FileKind.RECONSTRUCTION
