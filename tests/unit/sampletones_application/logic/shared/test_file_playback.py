from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_mix
from sampletones_shared.exceptions import InvalidReconstructionError, NoOutputDeviceError
from sampletones_shared.paths import extensions
from tests.suite.regeneration import HeldRegeneration
from tests.suite.sequencer import sample_reconstruction

RECONSTRUCTION_LOAD: Final[str] = "sampletones_application.logic.shared.file_playback.Reconstruction.load"
PREVIEWED_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]


@pytest.fixture
def regeneration() -> HeldRegeneration:
    return HeldRegeneration()


@pytest.fixture
def previews(renders: RenderCache, regeneration: HeldRegeneration) -> DocumentPreviews:
    return DocumentPreviews(renders, regeneration)


@pytest.fixture
def audio_device_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def playback(audio_device_manager: MagicMock, previews: DocumentPreviews) -> FilePlayback:
    playback = FilePlayback(audio_device_manager, previews)
    playback.on_error = MagicMock()
    return playback


def _document() -> Reconstruction:
    return sample_reconstruction(PREVIEWED_CHANNELS)


def _reconstruction_file(tmp_path: Path, name: str) -> Path:
    return tmp_path / f"{name}{extensions.EXT_FILE_RECONSTRUCTION}"


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

    def test_an_audio_file_asked_for_by_name_plays_at_normal_priority(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        playback.play(tmp_path / "audio.wav")

        audio_device_manager.play_file.assert_called_once_with(
            tmp_path / "audio.wav",
            update=False,
            priority=PlaybackPriority.NORMAL,
        )

    def test_a_priority_the_caller_names_is_the_one_it_plays_at(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        playback.play_at(tmp_path / "audio.wav", PlaybackPriority.PREVIEW)

        audio_device_manager.play_file.assert_called_once_with(
            tmp_path / "audio.wav",
            update=False,
            priority=PlaybackPriority.PREVIEW,
        )

    def test_a_file_of_another_kind_sounds_nothing(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        playback.play(tmp_path / "notes.txt")

        audio_device_manager.play_file.assert_not_called()
        audio_device_manager.play.assert_not_called()


class TestAReconstructionSoundsThroughThePreviews:
    """A reconstruction file is read and previewed whole: its sound is a worker's render, played at the priority
    asked once it lands, and the next file asked for replaces one still on its way.
    """

    def test_its_document_sounds_once_the_worker_lands_it_at_the_priority_asked(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        document = _document()
        with patch(RECONSTRUCTION_LOAD, return_value=document):
            playback.play_at(_reconstruction_file(tmp_path, "sample"), PlaybackPriority.PREVIEW)

        audio_device_manager.play.assert_not_called()
        regeneration.finish()

        audio_device_manager.play.assert_called_once()
        (played,) = audio_device_manager.play.call_args.args
        assert np.array_equal(played, rendered_mix(document))
        assert audio_device_manager.play.call_args.kwargs == {"update": False, "priority": PlaybackPriority.PREVIEW}

    def test_the_next_file_replaces_one_on_its_way(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        first = _document()
        second = _document()
        with patch(RECONSTRUCTION_LOAD, return_value=first):
            playback.play(_reconstruction_file(tmp_path, "first"))
        with patch(RECONSTRUCTION_LOAD, return_value=second):
            playback.play(_reconstruction_file(tmp_path, "second"))

        regeneration.finish()
        regeneration.finish()

        audio_device_manager.play.assert_called_once()
        (played,) = audio_device_manager.play.call_args.args
        assert np.array_equal(played, rendered_mix(second))

    def test_a_render_that_fails_reports(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        failure = RuntimeError("the worker fell over")
        with patch(RECONSTRUCTION_LOAD, return_value=_document()):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        regeneration.fail(failure)

        playback.on_error.assert_called_once_with(failure)
        audio_device_manager.play.assert_not_called()

    def test_a_device_refusing_at_the_landing_reports(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        refusal = NoOutputDeviceError("no device")
        audio_device_manager.play.side_effect = refusal
        with patch(RECONSTRUCTION_LOAD, return_value=_document()):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        regeneration.finish()

        playback.on_error.assert_called_once_with(refusal)


class TestAReconstructionThatWillNotRead:
    """A reconstruction file under the cursor is untrusted input: any load or playback failure in
    the domain (``SampleToNESError``) or I/O (``OSError``) families reports through ``on_error``;
    a failure outside those families is a bug and propagates."""

    @pytest.mark.parametrize(
        "error",
        [InvalidReconstructionError("corrupt"), PermissionError("denied")],
        ids=["domain", "io"],
    )
    def test_a_load_failure_is_reported(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
        error: Exception,
    ) -> None:
        with patch(RECONSTRUCTION_LOAD, side_effect=error):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        playback.on_error.assert_called_once_with(error)
        audio_device_manager.play.assert_not_called()
        assert regeneration.held == ()

    def test_an_unexpected_failure_propagates(self, playback: FilePlayback, tmp_path: Path) -> None:
        with patch(RECONSTRUCTION_LOAD, side_effect=RuntimeError("bug")), pytest.raises(RuntimeError):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        playback.on_error.assert_not_called()


class TestADeviceThatRefuses:
    """A device with no output in force refuses the playback, and the refusal reports through ``on_error``."""

    def test_an_audio_file_reports_the_refusal(
        self,
        playback: FilePlayback,
        audio_device_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        refusal = NoOutputDeviceError("no device")
        audio_device_manager.play_file.side_effect = refusal

        playback.play_at(tmp_path / "audio.wav", PlaybackPriority.PREVIEW)

        playback.on_error.assert_called_once_with(refusal)
