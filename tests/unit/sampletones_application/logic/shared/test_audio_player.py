from typing import Final, List, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from tests.suite.application import HeldQueue
from tests.suite.device import FakeAudioDevice

AUDIO_LENGTH: Final[int] = 100


def _player(*, owned: bool, paused: bool) -> Tuple[AudioPlayer, MagicMock]:
    device = MagicMock()
    device.is_owned_by.return_value = owned
    device.is_paused.return_value = paused
    return AudioPlayer(device), device


class Reports:
    """What a player tells its listeners: each position it reports, and each change of state."""

    def __init__(self, player: AudioPlayer) -> None:
        self.positions: List[int] = []
        self.state_changes = 0
        player.on_position_changed = self.positions.append
        player.on_change_audio_state = self._count_state_change

    def _count_state_change(self) -> None:
        self.state_changes += 1


@pytest.fixture
def device() -> FakeAudioDevice:
    return FakeAudioDevice()


@pytest.fixture
def player(device: FakeAudioDevice) -> AudioPlayer:
    player = AudioPlayer(device)
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player


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

    def test_an_owned_paused_player_moves_the_device_and_reports_the_sample(
        self,
        player: AudioPlayer,
        device: FakeAudioDevice,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        player.pause()
        reports = Reports(player)

        player.seek(40)

        assert device.position == 40
        assert player.current_position == 40
        assert reports.positions == [40]

    def test_a_seek_leaves_the_output_another_owner_holds_where_it_is(
        self,
        player: AudioPlayer,
        device: FakeAudioDevice,
    ) -> None:
        device.play(np.zeros(AUDIO_LENGTH, dtype=np.float32), priority=0, owner=object(), start=70)
        reports = Reports(player)

        moved = player.seek(40)

        assert (moved, device.position, player.current_position, reports.positions) == (
            False,
            70,
            START_OF_AUDIO,
            [],
        )


class TestPlayStartsWhereItIsAsked:
    def test_the_device_is_started_at_the_sample_asked_for(self, player: AudioPlayer, device: FakeAudioDevice) -> None:
        player.play(start=30)

        assert device.owner is player
        assert device.position == 30


class TestDeviceReportsCrossToTheRenderThread:
    """A report from the playback thread waits for the render loop, and reads the device when it runs."""

    def test_a_report_reaches_the_listeners_only_once_the_render_loop_runs_it(
        self,
        player: AudioPlayer,
        device: FakeAudioDevice,
        held_queue: HeldQueue,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        device.position = 64
        reports = Reports(player)

        player._on_device_position_changed(64)
        assert reports.positions == []

        held_queue.drain()

        assert reports.positions == [64]

    def test_a_report_overtaken_by_a_seek_reports_the_seek(
        self,
        player: AudioPlayer,
        device: FakeAudioDevice,
        held_queue: HeldQueue,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        device.position = 64
        player._on_device_position_changed(64)
        player.seek(40)
        reports = Reports(player)

        held_queue.drain()

        assert reports.positions == [40]

    def test_the_report_of_a_playback_winding_down_changes_the_state(
        self,
        player: AudioPlayer,
        device: FakeAudioDevice,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        device.stop()
        reports = Reports(player)

        player._on_device_position_changed(START_OF_AUDIO)

        assert reports.positions == [START_OF_AUDIO]
        assert reports.state_changes == 1

    def test_a_report_of_a_sounding_playback_keeps_the_state(self, player: AudioPlayer) -> None:
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)

        player._on_device_position_changed(64)

        assert reports.state_changes == 0
