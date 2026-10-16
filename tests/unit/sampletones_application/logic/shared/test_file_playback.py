from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.logic.shared.file_playback import FilePlayback
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.logic.shared.preview_player import PreviewPlayer
from sampletones_application.logic.shared.previews import DocumentPreviews
from sampletones_application.logic.shared.renders import RenderCache
from sampletones_core.audio.io import write_wave
from sampletones_core.audio.output import EndCause, Ending
from sampletones_core.constants.enums import ChannelName
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_mix
from sampletones_shared.exceptions import AudioReadError, InvalidReconstructionError, NoOutputDeviceError
from sampletones_shared.paths import extensions
from tests.suite.regeneration import HeldRegeneration
from tests.suite.sequencer import sample_reconstruction

RECONSTRUCTION_LOAD: Final[str] = "sampletones_application.logic.shared.file_playback.Reconstruction.load"
PREVIEWED_CHANNELS: Final[List[ChannelName]] = [ChannelName.PULSE1, ChannelName.TRIANGLE]
FILE_RATE: Final[int] = 96000
FILE_FRAMES: Final[int] = 480
LEFT: Final[float] = 0.5
RIGHT: Final[float] = 0.25
FLOAT_TOLERANCE: Final[float] = 1e-6


@pytest.fixture
def regeneration() -> HeldRegeneration:
    return HeldRegeneration()


@pytest.fixture
def previews(renders: RenderCache, regeneration: HeldRegeneration) -> DocumentPreviews:
    return DocumentPreviews(renders, regeneration)


@pytest.fixture
def preview_player() -> MagicMock:
    return MagicMock(spec=PreviewPlayer)


@pytest.fixture
def audio_file(tmp_path: Path) -> Path:
    """A stereo file at its own rate, the two channels apart so the mix shows."""
    path = tmp_path / "audio.wav"
    write_wave(path, FILE_RATE, np.stack([np.full(FILE_FRAMES, LEFT), np.full(FILE_FRAMES, RIGHT)], axis=1))
    return path


@pytest.fixture
def playback(preview_player: MagicMock, previews: DocumentPreviews) -> FilePlayback:
    playback = FilePlayback(preview_player, previews)
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
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        playback.play(audio_file)

        assert preview_player.play.call_args.kwargs["rank"] == PlaybackPriority.NORMAL
        assert preview_player.play.call_args.kwargs["listener"] is playback

    def test_a_priority_the_caller_names_is_the_one_it_plays_at(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        playback.play_at(audio_file, PlaybackPriority.PREVIEW)

        assert preview_player.play.call_args.kwargs["rank"] == PlaybackPriority.PREVIEW

    def test_an_audio_file_plays_as_one_channel_at_its_own_rate(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        playback.play(audio_file)

        (played,) = preview_player.play.call_args.args
        np.testing.assert_allclose(played, np.full(FILE_FRAMES, (LEFT + RIGHT) / 2), atol=FLOAT_TOLERANCE)
        assert preview_player.play.call_args.kwargs["sample_rate"] == FILE_RATE

    def test_a_file_of_another_kind_sounds_nothing(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        tmp_path: Path,
    ) -> None:
        playback.play(tmp_path / "notes.txt")

        preview_player.play.assert_not_called()


class TestAReconstructionSoundsThroughThePreviews:
    """A reconstruction file is read and previewed whole: its sound is a worker's render, played at the priority
    asked once it lands, and the next file asked for replaces one still on its way.
    """

    def test_its_document_sounds_once_the_worker_lands_it_at_the_priority_asked(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        document = _document()
        with patch(RECONSTRUCTION_LOAD, return_value=document):
            playback.play_at(_reconstruction_file(tmp_path, "sample"), PlaybackPriority.PREVIEW)

        preview_player.play.assert_not_called()
        regeneration.finish()

        preview_player.play.assert_called_once()
        (played,) = preview_player.play.call_args.args
        assert np.array_equal(played, rendered_mix(document))
        assert preview_player.play.call_args.kwargs == {
            "sample_rate": document.config.sample_rate,
            "rank": PlaybackPriority.PREVIEW,
            "listener": playback,
        }

    def test_the_next_file_replaces_one_on_its_way(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
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

        preview_player.play.assert_called_once()
        (played,) = preview_player.play.call_args.args
        assert np.array_equal(played, rendered_mix(second))

    def test_a_render_that_fails_reports(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        failure = RuntimeError("the worker fell over")
        with patch(RECONSTRUCTION_LOAD, return_value=_document()):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        regeneration.fail(failure)

        playback.on_error.assert_called_once_with(failure)
        preview_player.play.assert_not_called()

    def test_a_device_refusing_at_the_landing_reports(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
    ) -> None:
        refusal = NoOutputDeviceError("no device")
        preview_player.play.side_effect = refusal
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
        preview_player: MagicMock,
        regeneration: HeldRegeneration,
        tmp_path: Path,
        error: Exception,
    ) -> None:
        with patch(RECONSTRUCTION_LOAD, side_effect=error):
            playback.play(_reconstruction_file(tmp_path, "sample"))

        playback.on_error.assert_called_once_with(error)
        preview_player.play.assert_not_called()
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
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        refusal = NoOutputDeviceError("no device")
        preview_player.play.side_effect = refusal

        playback.play_at(audio_file, PlaybackPriority.PREVIEW)

        playback.on_error.assert_called_once_with(refusal)

    def test_a_file_failing_as_it_plays_reports_the_failure_once(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        failure = OSError("The device failed")
        playback.play(audio_file)

        playback.ended(preview_player.play.return_value, Ending.failure(failure))

        playback.on_error.assert_called_once_with(failure)

    def test_a_file_ending_of_itself_reports_nothing(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        audio_file: Path,
    ) -> None:
        playback.play(audio_file)

        playback.ended(preview_player.play.return_value, Ending.of(EndCause.FINISHED))

        playback.on_error.assert_not_called()


class TestAnAudioFileThatWillNotRead:
    """An audio file holding no audio the reader understands, or missing, reports through ``on_error`` and
    sounds nothing."""

    def test_an_unreadable_file_is_reported(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        tmp_path: Path,
    ) -> None:
        unreadable = tmp_path / "unreadable.wav"
        unreadable.write_bytes(b"neither a header nor samples")

        playback.play(unreadable)

        (reported,) = playback.on_error.call_args.args
        assert isinstance(reported, AudioReadError)
        preview_player.play.assert_not_called()

    def test_a_missing_file_is_reported(
        self,
        playback: FilePlayback,
        preview_player: MagicMock,
        tmp_path: Path,
    ) -> None:
        playback.play(tmp_path / "missing.wav")

        (reported,) = playback.on_error.call_args.args
        assert isinstance(reported, FileNotFoundError)
        preview_player.play.assert_not_called()
