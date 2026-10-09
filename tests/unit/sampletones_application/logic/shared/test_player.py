from typing import Final, List

import numpy as np
import pytest

from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from tests.suite.device import FakeAudioDevice

AUDIO_LENGTH: Final[int] = 1000


@pytest.fixture
def device() -> FakeAudioDevice:
    return FakeAudioDevice()


@pytest.fixture
def player(device: FakeAudioDevice) -> PlayerLogic:
    player = PlayerLogic(device)
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player


def _positions_reported(player: PlayerLogic) -> List[int]:
    positions: List[int] = []
    player.on_position_changed = positions.append
    return positions


class TestPlayFromPutsThePlayheadAtASample:
    """A pointed-at sample is where the playhead goes, whatever the player was doing."""

    def test_an_idle_player_starts_sounding_from_the_sample(self, player: PlayerLogic, device: FakeAudioDevice) -> None:
        player.play_from(400)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert device.position == 400

    def test_a_paused_player_moves_there_and_stays_paused(self, player: PlayerLogic, device: FakeAudioDevice) -> None:
        player.play()
        player.pause()
        positions = _positions_reported(player)

        player.play_from(400)

        assert player.is_paused() is True
        assert device.position == 400
        assert positions == [400]

    def test_a_sounding_player_moves_there_and_goes_on_sounding(
        self,
        player: PlayerLogic,
        device: FakeAudioDevice,
    ) -> None:
        player.play()
        device.position = 700
        positions = _positions_reported(player)

        player.play_from(400)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert device.position == 400
        assert positions == [400]

    def test_a_player_holding_no_audio_stays_idle(self, device: FakeAudioDevice) -> None:
        player = PlayerLogic(device)

        player.play_from(400)

        assert player.is_playing() is False
        assert device.audio is None

    def test_play_starts_from_the_beginning(self, player: PlayerLogic, device: FakeAudioDevice) -> None:
        player.play_from(400)
        player.stop()

        player.play()

        assert device.position == START_OF_AUDIO
