from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback.router import PlaybackRouter


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
