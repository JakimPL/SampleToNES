from typing import List
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError

GUARDED_COMMANDS = ("play", "pause_or_resume")


@pytest.fixture
def player_logic() -> MagicMock:
    return MagicMock()


@pytest.fixture
def failures() -> MagicMock:
    return MagicMock()


@pytest.fixture
def guarded_player(player_logic: MagicMock, failures: MagicMock) -> GuardedPlayer:
    return GuardedPlayer(player_logic, failures=failures)


class TestGuardedCommands:
    """The transport commands that can raise ``PlaybackError`` hand it to the presenter instead of
    propagating, so a panel hook or the playback router can invoke them bare.

    A start that fails at once reads the way a failure on the playing thread does, so one refusal reads
    alike however soon the device refused.
    """

    @pytest.mark.parametrize("command", GUARDED_COMMANDS)
    def test_delegates_to_the_logic(
        self,
        guarded_player: GuardedPlayer,
        player_logic: MagicMock,
        failures: MagicMock,
        command: str,
    ) -> None:
        getattr(guarded_player, command)()

        getattr(player_logic, command).assert_called_once_with()
        failures.present_playing_failure.assert_not_called()

    @pytest.mark.parametrize("command", GUARDED_COMMANDS)
    @pytest.mark.parametrize(
        "exception",
        [PlaybackError("device unavailable"), NoOutputDeviceError("no device")],
        ids=["playback", "no_output"],
    )
    def test_a_playback_error_reaches_the_presenter(
        self,
        guarded_player: GuardedPlayer,
        player_logic: MagicMock,
        failures: MagicMock,
        command: str,
        exception: PlaybackError,
    ) -> None:
        getattr(player_logic, command).side_effect = exception

        getattr(guarded_player, command)()

        failures.present_playing_failure.assert_called_once_with(exception)


class TestAGuardedRun:
    """A command beyond the transport runs under the same boundary the transport commands keep."""

    def test_the_command_runs(self, guarded_player: GuardedPlayer, failures: MagicMock) -> None:
        ran: List[int] = []

        guarded_player.run_guarded(lambda: ran.append(400))

        assert ran == [400]
        failures.present_playing_failure.assert_not_called()

    def test_a_playback_error_reaches_the_presenter(self, guarded_player: GuardedPlayer, failures: MagicMock) -> None:
        exception = PlaybackError("device unavailable")

        def failing() -> None:
            raise exception

        guarded_player.run_guarded(failing)

        failures.present_playing_failure.assert_called_once_with(exception)
