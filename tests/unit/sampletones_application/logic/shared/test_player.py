from typing import Final, List

import numpy as np
import pytest

from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.logic.shared.player import PlayerLogic
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio.output import BufferSource, Ending
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from tests.suite.audio.output import FakeAudioOutput

AUDIO_LENGTH: Final[int] = 1000
POINTED: Final[int] = 400
SOUNDING: Final[int] = 700
DEVICE_FAILURE: Final[str] = "The device failed"


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def player(output: FakeAudioOutput) -> PlayerLogic:
    player = PlayerLogic(AudioPlayer(output))
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player


def _positions_reported(player: PlayerLogic) -> List[int]:
    positions: List[int] = []
    player.on_position_changed = positions.append
    return positions


def _source(output: FakeAudioOutput) -> BufferSource:
    source = output.claim(output.latest).source
    assert isinstance(source, BufferSource)
    return source


class TestPlayFromPutsThePlayheadAtASample:
    """A pointed-at sample is where the playhead goes, whatever the player was doing."""

    def test_an_idle_player_starts_sounding_from_the_sample(self, player: PlayerLogic, output: FakeAudioOutput) -> None:
        player.play_from(POINTED)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert _source(output).position == POINTED

    def test_a_paused_player_moves_there_and_stays_paused(self, player: PlayerLogic, output: FakeAudioOutput) -> None:
        player.play()
        player.pause()
        positions = _positions_reported(player)

        player.play_from(POINTED)

        assert player.is_paused() is True
        assert _source(output).position == POINTED
        assert positions == [POINTED]
        assert len(output.playbacks) == 1

    def test_a_sounding_player_moves_there_and_goes_on_sounding(
        self,
        player: PlayerLogic,
        output: FakeAudioOutput,
    ) -> None:
        player.play()
        output.report(output.latest, SOUNDING)
        positions = _positions_reported(player)

        player.play_from(POINTED)

        assert player.is_playing() is True
        assert player.is_paused() is False
        assert _source(output).position == POINTED
        assert positions == [POINTED]

    def test_a_player_whose_sound_is_ending_starts_a_new_one_from_the_sample(
        self,
        player: PlayerLogic,
        output: FakeAudioOutput,
    ) -> None:
        player.play()
        ending = output.latest
        output.stop(ending)

        player.play_from(POINTED)

        assert output.latest is not ending
        assert _source(output).position == POINTED

    def test_a_player_holding_no_audio_stays_idle(self, output: FakeAudioOutput) -> None:
        player = PlayerLogic(AudioPlayer(output))

        player.play_from(POINTED)

        assert player.is_playing() is False
        assert output.playbacks == []

    def test_play_starts_from_the_beginning(self, player: PlayerLogic, output: FakeAudioOutput) -> None:
        player.play_from(POINTED)
        player.stop()

        player.play()

        assert _source(output).position == START_OF_AUDIO


class TestFailures:
    """A failure of the playback reaches the player's ``on_error``, once."""

    def test_a_failure_is_told_once(self, player: PlayerLogic, output: FakeAudioOutput) -> None:
        errors: List[Exception] = []
        player.on_error = errors.append
        player.play()
        failure = OSError(DEVICE_FAILURE)

        output.end(output.latest, Ending.failure(failure))

        assert errors == [failure]
        assert player.is_playing() is False
