from typing import Any, Callable, Final, List, Optional

import numpy as np
import pytest

from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO

AUDIO_LENGTH: Final[int] = 1000


class FakeDevice:
    """The shared output as one player sees it: who holds it, where it stands, and whether it waits."""

    def __init__(self) -> None:
        self.owner: Optional[Any] = None
        self.paused: bool = False
        self.position: int = START_OF_AUDIO
        self.audio: Optional[np.ndarray] = None

    def set_position_callback(self, _callback: Optional[Callable[[int], None]]) -> None:
        return None

    def replace_audio(self, _audio: np.ndarray, *, owner: Optional[Any] = None) -> bool:
        return False

    def play(
        self,
        audio: np.ndarray,
        *,
        priority: int,
        owner: Optional[Any],
        start: int,
    ) -> bool:
        self.audio = audio
        self.owner = owner
        self.paused = False
        self.position = max(0, min(start, len(audio)))
        return True

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def stop(self) -> None:
        self.owner = None
        self.paused = False
        self.position = START_OF_AUDIO

    def set_position(self, position: int) -> None:
        self.position = position

    def is_owned_by(self, owner: Any) -> bool:
        return owner is not None and self.owner is owner

    def is_paused(self) -> bool:
        return self.paused


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice()


@pytest.fixture
def player(device: FakeDevice) -> PlayerLogic:
    player = PlayerLogic(device)
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player


def _positions_reported(player: PlayerLogic) -> List[int]:
    positions: List[int] = []
    player.on_position_changed = positions.append
    return positions


class TestPlayFromPutsThePlayheadAtASample:
    """A pointed-at sample is where the playhead goes, whatever the player was doing."""

    def test_an_idle_player_starts_sounding_from_the_sample(self, player: PlayerLogic, device: FakeDevice) -> None:
        player.play_from(400)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert device.position == 400

    def test_a_paused_player_moves_there_and_stays_paused(self, player: PlayerLogic, device: FakeDevice) -> None:
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
        device: FakeDevice,
    ) -> None:
        player.play()
        device.position = 700
        positions = _positions_reported(player)

        player.play_from(400)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert device.position == 400
        assert positions == [400]

    def test_a_player_holding_no_audio_stays_idle(self, device: FakeDevice) -> None:
        player = PlayerLogic(device)

        player.play_from(400)

        assert player.is_playing() is False
        assert device.audio is None

    def test_play_starts_from_the_beginning(self, player: PlayerLogic, device: FakeDevice) -> None:
        player.play_from(400)
        player.stop()

        player.play()

        assert device.position == START_OF_AUDIO
