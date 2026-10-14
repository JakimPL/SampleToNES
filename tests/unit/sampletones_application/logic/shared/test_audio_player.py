from typing import Final, List

import numpy as np
import pytest

from sampletones_application.logic.shared.audio_player import AudioPlayer
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.shared.audio_data import AudioData
from sampletones_core.audio.output import BufferSource, EndCause, Ending
from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, START_OF_AUDIO
from sampletones_shared.exceptions import NoOutputDeviceError
from tests.suite.audio.output import FakeAudioOutput

AUDIO_LENGTH: Final[int] = 100
SEEK_TARGET: Final[int] = 40
STARTED_AT: Final[int] = 30
REPORTED: Final[int] = 64
FILE_RATE: Final[int] = 48000
DEVICE_FAILURE: Final[str] = "The device failed"


class Reports:
    """What a player tells its listeners: each position it draws, each change of state, and each failure."""

    def __init__(self, player: AudioPlayer) -> None:
        self.positions: List[int] = []
        self.errors: List[Exception] = []
        self.state_changes = 0
        player.on_position_changed = self.positions.append
        player.on_change_audio_state = self._count_state_change
        player.on_error = self.errors.append

    def _count_state_change(self) -> None:
        self.state_changes += 1


@pytest.fixture
def output() -> FakeAudioOutput:
    return FakeAudioOutput()


@pytest.fixture
def player(output: FakeAudioOutput) -> AudioPlayer:
    player = AudioPlayer(output)
    player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
    return player


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a buffer told a failure between reads: {error}")


def _source(output: FakeAudioOutput) -> BufferSource:
    source = output.claim(output.latest).source
    assert isinstance(source, BufferSource)
    return source


class TestEngagement:
    """A player reads itself engaged while the playback it started holds the output, and idle once it ends."""

    def test_a_player_whose_playback_holds_the_output_is_engaged(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=START_OF_AUDIO)

        assert player.is_playing
        assert output.claim(output.latest).rank == PlaybackPriority.NORMAL

    def test_a_player_whose_playback_was_taken_is_idle(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)

        output.end(output.latest, Ending.of(EndCause.TAKEN))

        assert not player.is_playing

    def test_a_declined_play_leaves_the_player_idle(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        output.declining = True

        player.play(start=START_OF_AUDIO)

        assert not player.is_playing

    def test_paused_requires_the_playback_to_hold_the_output(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        player.pause()
        paused = player.is_paused

        output.end(output.latest, Ending.of(EndCause.TAKEN))

        assert paused
        assert not player.is_paused


class TestPlay:
    """A play sounds the loaded audio at the rate it was made at, from the sample asked for."""

    def test_the_sound_starts_at_the_sample_asked_for(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=STARTED_AT)

        assert _source(output).position == STARTED_AT
        assert player.current_position == STARTED_AT

    def test_the_sound_plays_at_the_rate_its_audio_was_made_at(self, output: FakeAudioOutput) -> None:
        player = AudioPlayer(output)
        player.load_audio_data(AudioData.from_array(np.zeros(AUDIO_LENGTH, dtype=np.float32), FILE_RATE))
        player.play(start=START_OF_AUDIO)
        source = _source(output)
        source.begin(DEFAULT_SAMPLE_RATE, _unexpected)

        block = np.zeros(AUDIO_LENGTH * 2, dtype=np.float32)
        frames = source.read_into(block).frames

        assert frames == pytest.approx(AUDIO_LENGTH * DEFAULT_SAMPLE_RATE / FILE_RATE, abs=2)

    def test_a_play_over_its_own_sound_stops_that_one(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)
        first = output.latest

        player.play(start=START_OF_AUDIO)

        assert output.claim(first).stopped
        assert output.latest is not first

    def test_a_player_holding_no_audio_plays_nothing(self, output: FakeAudioOutput) -> None:
        player = AudioPlayer(output)

        player.play(start=START_OF_AUDIO)

        assert output.playbacks == []

    def test_a_refusal_reaches_the_caller(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        refusal = NoOutputDeviceError("no device")
        output.refusal = refusal
        reports = Reports(player)

        with pytest.raises(NoOutputDeviceError) as raised:
            player.play(start=START_OF_AUDIO)

        assert raised.value is refusal
        assert reports.state_changes == 0


class TestSeek:
    """A seek moves the player's own playback while it plays and draws the sample it moved to; one whose end
    is decided refuses, so the caller starts a new one."""

    def test_a_paused_player_moves_and_draws_the_sample(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)
        player.pause()
        reports = Reports(player)

        moved = player.seek(SEEK_TARGET)

        assert moved
        assert _source(output).position == SEEK_TARGET
        assert player.current_position == SEEK_TARGET
        assert reports.positions == [SEEK_TARGET]

    def test_a_playback_whose_end_is_decided_refuses_the_seek(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        output.stop(output.latest)
        reports = Reports(player)

        moved = player.seek(SEEK_TARGET)

        assert not moved
        assert reports.positions == []

    def test_an_idle_player_refuses_the_seek(self, player: AudioPlayer) -> None:
        assert not player.seek(SEEK_TARGET)


class TestReports:
    """The player draws the positions of the playback it holds, and moves its mark off once that one ends."""

    def test_a_position_of_the_held_playback_is_drawn(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)

        output.report(output.latest, REPORTED)

        assert reports.positions == [REPORTED]
        assert player.current_position == REPORTED

    def test_a_position_of_an_older_playback_is_ignored(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)
        older = output.latest
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)

        output.report(older, REPORTED)

        assert reports.positions == []

    def test_the_end_moves_the_mark_off_and_changes_the_state(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)

        output.end(output.latest, Ending.of(EndCause.FINISHED))

        assert reports.positions == [START_OF_AUDIO]
        assert reports.state_changes == 1
        assert reports.errors == []

    def test_a_failure_is_told_once(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)
        failure = OSError(DEVICE_FAILURE)

        output.end(output.latest, Ending.failure(failure))

        assert reports.errors == [failure]

    def test_the_end_of_an_older_playback_leaves_the_newer_one_alone(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=START_OF_AUDIO)
        older = output.latest
        player.play(start=START_OF_AUDIO)
        reports = Reports(player)

        output.end(older, Ending.of(EndCause.STOPPED))

        assert player.is_playing
        assert reports.positions == []
        assert reports.state_changes == 0


class TestStop:
    """A stop ends the player's own playback, and leaves every other sound alone."""

    def test_a_stop_ends_its_own_playback_and_moves_the_mark_off(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=STARTED_AT)
        reports = Reports(player)

        player.stop()

        assert output.claim(output.latest).stopped
        assert reports.positions == [START_OF_AUDIO]
        assert not player.is_playing

    def test_a_stop_of_an_idle_player_stops_nothing(self, player: AudioPlayer, output: FakeAudioOutput) -> None:
        player.stop()

        assert output.playbacks == []


class TestReplace:
    """Audio loaded under a playback reaches its source, keeping the moment the playback reached."""

    def test_new_audio_reaches_the_playback_holding_the_output(
        self,
        player: AudioPlayer,
        output: FakeAudioOutput,
    ) -> None:
        player.play(start=STARTED_AT)

        player.load_audio_data(AudioData.from_array(np.ones(AUDIO_LENGTH, dtype=np.float32), DEFAULT_SAMPLE_RATE))
        source = _source(output)
        source.begin(DEFAULT_SAMPLE_RATE, _unexpected)
        block = np.zeros(AUDIO_LENGTH, dtype=np.float32)
        source.read_into(block)

        assert block[0] == 1.0
