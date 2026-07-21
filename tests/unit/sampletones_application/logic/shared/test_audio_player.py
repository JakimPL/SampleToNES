from typing import Tuple
from unittest.mock import MagicMock

from sampletones_application.logic.shared.audio_player import AudioPlayer


def _player(*, owned: bool, paused: bool) -> Tuple[AudioPlayer, MagicMock]:
    device = MagicMock()
    device.is_owned_by.return_value = owned
    device.is_paused.return_value = paused
    return AudioPlayer(device), device


class TestEngagementFollowsOwnership:
    """A player reports itself engaged only while its own audio owns the shared output."""

    def test_playing_when_it_owns_the_output(self) -> None:
        player, device = _player(owned=True, paused=False)

        assert player.is_playing is True
        device.is_owned_by.assert_called_with(player)

    def test_not_playing_when_another_owner_holds_the_output(self) -> None:
        player, _ = _player(owned=False, paused=False)

        assert player.is_playing is False

    def test_paused_requires_ownership(self) -> None:
        foreign, _ = _player(owned=False, paused=True)
        owned, _ = _player(owned=True, paused=True)

        assert foreign.is_paused is False
        assert owned.is_paused is True
