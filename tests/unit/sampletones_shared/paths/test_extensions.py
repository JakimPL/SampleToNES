from pathlib import Path

from sampletones_shared.paths.extensions import is_audio_file
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
