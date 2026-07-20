from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback.preview import PreviewPlayer

PLAY_COMMANDS = ("play", "pause_or_resume")


@pytest.fixture
def audio_device_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def preview_player(audio_device_manager: MagicMock) -> PreviewPlayer:
    return PreviewPlayer(audio_device_manager)


class TestPreviewPlayer:
    """Stop-only transport: state queries mirror the shared output device, ``stop``
    silences it, and the play commands leave the device untouched."""

    def test_stop_silences_the_device(
        self,
        preview_player: PreviewPlayer,
        audio_device_manager: MagicMock,
    ) -> None:
        preview_player.stop()

        audio_device_manager.stop.assert_called_once_with()

    @pytest.mark.parametrize("playing", [True, False])
    def test_is_playing_mirrors_the_device(
        self,
        preview_player: PreviewPlayer,
        audio_device_manager: MagicMock,
        playing: bool,
    ) -> None:
        audio_device_manager.is_playing.return_value = playing

        assert preview_player.is_playing() is playing

    @pytest.mark.parametrize("paused", [True, False])
    def test_is_paused_mirrors_the_device(
        self,
        preview_player: PreviewPlayer,
        audio_device_manager: MagicMock,
        paused: bool,
    ) -> None:
        audio_device_manager.is_paused.return_value = paused

        assert preview_player.is_paused() is paused

    def test_reports_audio_as_unloaded(self, preview_player: PreviewPlayer) -> None:
        assert preview_player.is_loaded() is False

    @pytest.mark.parametrize("command", PLAY_COMMANDS)
    def test_play_commands_leave_the_device_untouched(
        self,
        preview_player: PreviewPlayer,
        audio_device_manager: MagicMock,
        command: str,
    ) -> None:
        getattr(preview_player, command)()

        assert audio_device_manager.method_calls == []
