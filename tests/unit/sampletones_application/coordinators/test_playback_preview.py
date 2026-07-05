from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback import PlaybackRouter, PreviewPlayer

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


@dataclass(frozen=True)
class EnablementCase:
    label: str
    loaded: bool
    playing: bool
    play_enabled: bool
    stop_enabled: bool


enablement_cases = [
    EnablementCase("idle_without_audio", loaded=False, playing=False, play_enabled=False, stop_enabled=False),
    EnablementCase("preview_playing", loaded=False, playing=True, play_enabled=False, stop_enabled=True),
    EnablementCase("loaded_and_idle", loaded=True, playing=False, play_enabled=True, stop_enabled=False),
    EnablementCase("loaded_and_playing", loaded=True, playing=True, play_enabled=True, stop_enabled=True),
]


def _router(player: MagicMock) -> PlaybackRouter:
    return PlaybackRouter(lambda: player, language_manager=MagicMock())


class TestPlaybackRouterEnablement:
    """Play follows loaded audio; stop follows audible output, so a one-shot preview
    can be silenced even from a tab whose player holds no audio."""

    @pytest.mark.parametrize("case", enablement_cases, ids=lambda case: case.label)
    def test_transport_enablement(self, case: EnablementCase) -> None:
        player = MagicMock()
        player.is_loaded.return_value = case.loaded
        player.is_playing.return_value = case.playing

        router = _router(player)

        assert router.is_play_enabled is case.play_enabled
        assert router.is_stop_enabled is case.stop_enabled

    def test_stop_routes_to_the_active_player(self) -> None:
        player = MagicMock()

        _router(player).stop()

        player.stop.assert_called_once_with()
