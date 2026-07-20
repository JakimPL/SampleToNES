from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.playback.prioritized import PrioritizedPreviewPlayer


@pytest.fixture
def primary() -> MagicMock:
    player = MagicMock()
    player.is_playing.return_value = False
    player.is_paused.return_value = False
    player.is_loaded.return_value = False
    return player


@pytest.fixture
def audio_device_manager() -> MagicMock:
    device = MagicMock()
    device.is_playing.return_value = False
    device.is_paused.return_value = False
    return device


@pytest.fixture
def player(primary: MagicMock, audio_device_manager: MagicMock) -> PrioritizedPreviewPlayer:
    return PrioritizedPreviewPlayer(primary, audio_device_manager=audio_device_manager)


class TestPlayGivesPrimaryPriority:
    """``play`` always starts the primary player and leaves the device untouched."""

    def test_play_starts_the_primary(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
        audio_device_manager: MagicMock,
    ) -> None:
        player.play()

        primary.play.assert_called_once_with()
        assert audio_device_manager.method_calls == []

    def test_is_loaded_follows_the_primary(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
    ) -> None:
        primary.is_loaded.return_value = True

        assert player.is_loaded() is True


@pytest.mark.parametrize("engaged_state", ["playing", "paused"])
class TestPrimaryEngagedOwnsTransport:
    """While the primary is playing or paused, pause/resume and stop route to it and
    the shared device is left alone."""

    def _engage(self, primary: MagicMock, engaged_state: str) -> None:
        primary.is_playing.return_value = engaged_state == "playing"
        primary.is_paused.return_value = engaged_state == "paused"

    def test_pause_or_resume_routes_to_the_primary(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
        audio_device_manager: MagicMock,
        engaged_state: str,
    ) -> None:
        self._engage(primary, engaged_state)

        player.pause_or_resume()

        primary.pause_or_resume.assert_called_once_with()
        audio_device_manager.pause.assert_not_called()
        audio_device_manager.resume.assert_not_called()

    def test_stop_routes_to_the_primary(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
        audio_device_manager: MagicMock,
        engaged_state: str,
    ) -> None:
        self._engage(primary, engaged_state)

        player.stop()

        primary.stop.assert_called_once_with()
        audio_device_manager.stop.assert_not_called()


class TestIdlePrimaryManagesThePreview:
    """While the primary is idle, transport commands act on the shared output device
    so a sounding preview can be paused, resumed, and stopped."""

    def test_stop_silences_the_device(
        self,
        player: PrioritizedPreviewPlayer,
        audio_device_manager: MagicMock,
    ) -> None:
        audio_device_manager.is_playing.return_value = True

        player.stop()

        audio_device_manager.stop.assert_called_once_with()

    def test_pause_or_resume_pauses_a_playing_preview(
        self,
        player: PrioritizedPreviewPlayer,
        audio_device_manager: MagicMock,
    ) -> None:
        audio_device_manager.is_playing.return_value = True
        audio_device_manager.is_paused.return_value = False

        player.pause_or_resume()

        audio_device_manager.pause.assert_called_once_with()
        audio_device_manager.resume.assert_not_called()

    def test_pause_or_resume_resumes_a_paused_preview(
        self,
        player: PrioritizedPreviewPlayer,
        audio_device_manager: MagicMock,
    ) -> None:
        audio_device_manager.is_playing.return_value = True
        audio_device_manager.is_paused.return_value = True

        player.pause_or_resume()

        audio_device_manager.resume.assert_called_once_with()
        audio_device_manager.pause.assert_not_called()

    def test_pause_or_resume_is_a_no_op_when_silent(
        self,
        player: PrioritizedPreviewPlayer,
        audio_device_manager: MagicMock,
    ) -> None:
        player.pause_or_resume()

        audio_device_manager.pause.assert_not_called()
        audio_device_manager.resume.assert_not_called()


@dataclass(frozen=True)
class StateCase:
    label: str
    primary_state: bool
    device_state: bool
    expected: bool


state_cases = [
    StateCase("neither", primary_state=False, device_state=False, expected=False),
    StateCase("primary_only", primary_state=True, device_state=False, expected=True),
    StateCase("device_only", primary_state=False, device_state=True, expected=True),
    StateCase("both", primary_state=True, device_state=True, expected=True),
]


class TestStateReportsEitherSource:
    """``is_playing`` / ``is_paused`` report the primary or the shared device, so the
    toolbar lights up for a preview as well as for the primary."""

    @pytest.mark.parametrize("case", state_cases, ids=lambda case: case.label)
    def test_is_playing(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
        audio_device_manager: MagicMock,
        case: StateCase,
    ) -> None:
        primary.is_playing.return_value = case.primary_state
        audio_device_manager.is_playing.return_value = case.device_state

        assert player.is_playing() is case.expected

    @pytest.mark.parametrize("case", state_cases, ids=lambda case: case.label)
    def test_is_paused(
        self,
        player: PrioritizedPreviewPlayer,
        primary: MagicMock,
        audio_device_manager: MagicMock,
        case: StateCase,
    ) -> None:
        primary.is_paused.return_value = case.primary_state
        audio_device_manager.is_paused.return_value = case.device_state

        assert player.is_paused() is case.expected
