from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback.guard import GuardedPlayer
from sampletones_shared.exceptions import PlaybackError

GUARDED_COMMANDS = ("play", "pause_or_resume")


@pytest.fixture
def player_logic() -> MagicMock:
    return MagicMock()


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def guarded_player(player_logic: MagicMock, dialogs: MagicMock) -> GuardedPlayer:
    return GuardedPlayer(player_logic, dialogs=dialogs, error_message="playback failed")


class TestGuardedCommands:
    """The transport commands that can raise ``PlaybackError`` surface it as a dialog instead of
    propagating, so a panel hook or the playback router can invoke them bare."""

    @pytest.mark.parametrize("command", GUARDED_COMMANDS)
    def test_delegates_to_the_logic(
        self,
        guarded_player: GuardedPlayer,
        player_logic: MagicMock,
        dialogs: MagicMock,
        command: str,
    ) -> None:
        getattr(guarded_player, command)()

        getattr(player_logic, command).assert_called_once_with()
        dialogs.show_error.assert_not_called()

    @pytest.mark.parametrize("command", GUARDED_COMMANDS)
    def test_playback_error_becomes_a_dialog(
        self,
        guarded_player: GuardedPlayer,
        player_logic: MagicMock,
        dialogs: MagicMock,
        command: str,
    ) -> None:
        exception = PlaybackError("device unavailable")
        getattr(player_logic, command).side_effect = exception

        getattr(guarded_player, command)()

        dialogs.show_error.assert_called_once_with(exception, "playback failed")


class TestPassThroughs:
    """Stop and the status queries delegate without a guard, matching the logic's own surface."""

    def test_stop_delegates(self, guarded_player: GuardedPlayer, player_logic: MagicMock) -> None:
        guarded_player.stop()

        player_logic.stop.assert_called_once_with()

    def test_queries_reflect_the_logic(self, guarded_player: GuardedPlayer, player_logic: MagicMock) -> None:
        player_logic.is_playing.return_value = True
        player_logic.is_paused.return_value = False
        player_logic.is_loaded.return_value = True

        assert guarded_player.is_playing() is True
        assert guarded_player.is_paused() is False
        assert guarded_player.is_loaded() is True
