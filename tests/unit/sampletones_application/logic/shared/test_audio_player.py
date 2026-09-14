from typing import Final, List, Tuple
from unittest.mock import MagicMock

import numpy as np

from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE

AUDIO_LENGTH: Final[int] = 100


def _player(*, owned: bool, paused: bool) -> Tuple[AudioPlayer, MagicMock]:
    device = MagicMock()
    device.is_owned_by.return_value = owned
    device.is_paused.return_value = paused
    return AudioPlayer(device), device


def _loaded_player(*, owned: bool, paused: bool) -> Tuple[AudioPlayer, MagicMock]:
    player, device = _player(owned=owned, paused=paused)
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player, device


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


class TestSeekMovesItsOwnPlayback:
    """A seek reaches the device only while the player's own audio holds it, and reports where it went."""

    def test_an_owned_paused_player_moves_the_device_and_reports_the_sample(self) -> None:
        player, device = _loaded_player(owned=True, paused=True)
        reported: List[int] = []
        player.on_position_changed = reported.append

        player.seek(40)

        device.set_position.assert_called_once_with(40)
        assert player.current_position == 40
        assert reported == [40]

    def test_a_seek_past_the_audio_is_clamped_to_its_end(self) -> None:
        player, device = _loaded_player(owned=True, paused=False)
        reported: List[int] = []
        player.on_position_changed = reported.append

        player.seek(AUDIO_LENGTH + 50)

        device.set_position.assert_called_once_with(AUDIO_LENGTH)
        assert reported == [AUDIO_LENGTH]

    def test_a_seek_leaves_the_output_another_owner_holds_where_it_is(self) -> None:
        player, device = _loaded_player(owned=False, paused=False)
        reported: List[int] = []
        player.on_position_changed = reported.append

        player.seek(40)

        device.set_position.assert_not_called()
        assert reported == []


class TestPlayStartsWhereItIsAsked:
    def test_the_device_is_started_at_the_sample_asked_for(self) -> None:
        player, device = _loaded_player(owned=False, paused=False)

        player.play(start=30)

        assert device.play.call_args.kwargs["start"] == 30
        assert device.play.call_args.kwargs["owner"] is player
