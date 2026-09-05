from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_shared.exceptions import InvalidReconstructionError
from sampletones_shared.paths import extensions

RECONSTRUCTION_LOAD = "sampletones_application.logic.shared.file_playback.Reconstruction.load"


class TestWhatItSounds:
    """A file the player knows how to sound is a reconstruction or an audio file."""

    def test_a_reconstruction_sounds(self, tmp_path: Path) -> None:
        assert FilePlayback.plays(tmp_path / f"song{extensions.EXT_FILE_RECONSTRUCTION}") is True

    def test_an_audio_file_sounds(self, tmp_path: Path) -> None:
        assert FilePlayback.plays(tmp_path / "audio.wav") is True

    def test_anything_else_stays_quiet(self, tmp_path: Path) -> None:
        assert FilePlayback.plays(tmp_path / "notes.txt") is False


class TestHowItSounds:
    """A file named on demand outranks the preview a selection sounds on its own."""

    def test_an_audio_file_asked_for_by_name_plays_at_normal_priority(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()

        FilePlayback(audio_device_manager).play(tmp_path / "audio.wav")

        audio_device_manager.play_file.assert_called_once_with(
            tmp_path / "audio.wav",
            update=False,
            priority=PlaybackPriority.NORMAL,
        )

    def test_a_priority_the_caller_names_is_the_one_it_plays_at(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()

        FilePlayback(audio_device_manager).play_at(tmp_path / "audio.wav", PlaybackPriority.PREVIEW)

        audio_device_manager.play_file.assert_called_once_with(
            tmp_path / "audio.wav",
            update=False,
            priority=PlaybackPriority.PREVIEW,
        )

    def test_a_file_of_another_kind_sounds_nothing(self, tmp_path: Path) -> None:
        audio_device_manager = MagicMock()

        FilePlayback(audio_device_manager).play(tmp_path / "notes.txt")

        audio_device_manager.play_file.assert_not_called()
        audio_device_manager.play.assert_not_called()


class TestAReconstructionThatWillNotRead:
    """A reconstruction file under the cursor is untrusted input: any load or playback failure in
    the domain (``SampleToNESError``) or I/O (``OSError``) families reports through ``on_error``;
    a failure outside those families is a bug and propagates."""

    @pytest.mark.parametrize(
        "error",
        [InvalidReconstructionError("corrupt"), PermissionError("denied")],
        ids=["domain", "io"],
    )
    def test_a_load_failure_is_reported(self, tmp_path: Path, error: Exception) -> None:
        audio_device_manager = MagicMock()
        playback = FilePlayback(audio_device_manager)
        playback.on_error = MagicMock()

        with patch(RECONSTRUCTION_LOAD, side_effect=error):
            playback.play(tmp_path / f"sample{extensions.EXT_FILE_RECONSTRUCTION}")

        playback.on_error.assert_called_once_with(error)
        audio_device_manager.play.assert_not_called()

    def test_an_unexpected_failure_propagates(self, tmp_path: Path) -> None:
        playback = FilePlayback(MagicMock())
        playback.on_error = MagicMock()

        with patch(RECONSTRUCTION_LOAD, side_effect=RuntimeError("bug")), pytest.raises(RuntimeError):
            playback.play(tmp_path / f"sample{extensions.EXT_FILE_RECONSTRUCTION}")

        playback.on_error.assert_not_called()
