from typing import Final, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT
from sampletones_shared.exceptions import NoOutputDeviceError, PlaybackError

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
NO_OUTPUT_MESSAGE: Final[str] = "global.dialog.message.no_audio_output"
NO_OUTPUT_TITLE: Final[str] = "global.dialog.title.no_audio_output"
ERROR_MESSAGE: Final[str] = "playback failed"
PLAYING_FAILURE_MESSAGE: Final[str] = "global.dialog.message.audio_playback_error"


@pytest.fixture(name="dialogs")
def dialogs_fixture() -> MagicMock:
    return MagicMock()


@pytest.fixture(name="presenter")
def presenter_fixture(dialogs: MagicMock) -> PlaybackFailurePresenter:
    return PlaybackFailurePresenter(dialogs=dialogs, language_manager=LANGUAGE_MANAGER)


class TestNoOutput:
    """A machine offering no audio output reads as a plain notice, whatever line the caller offers."""

    @pytest.mark.parametrize("message", [ERROR_MESSAGE, None], ids=["with_a_message", "without_a_message"])
    def test_a_missing_output_reads_as_a_notice(
        self,
        presenter: PlaybackFailurePresenter,
        dialogs: MagicMock,
        message: Optional[str],
    ) -> None:
        presenter.present(NoOutputDeviceError("no device"), message=message)

        dialogs.show_info.assert_called_once_with(
            TAG_GLOBAL_DIALOG_NO_AUDIO_OUTPUT,
            LANGUAGE_MANAGER[NO_OUTPUT_MESSAGE],
            LANGUAGE_MANAGER[NO_OUTPUT_TITLE],
            modal=True,
        )
        dialogs.show_error.assert_not_called()


class TestOtherFailures:
    """Any other failure reads as an error report opening with the caller's line."""

    @pytest.mark.parametrize(
        "exception",
        [PlaybackError("stream refused"), OSError("device busy")],
        ids=["playback", "io"],
    )
    def test_a_failure_reads_as_an_error(
        self,
        presenter: PlaybackFailurePresenter,
        dialogs: MagicMock,
        exception: Exception,
    ) -> None:
        presenter.present(exception, message=ERROR_MESSAGE)

        dialogs.show_error.assert_called_once_with(exception, ERROR_MESSAGE)
        dialogs.show_info.assert_not_called()


class TestAFailureWhilePlaying:
    """A playback that fails on the thread playing it reads the same whichever source played it."""

    def test_a_refused_stream_reads_as_an_error_with_the_playback_line(
        self,
        presenter: PlaybackFailurePresenter,
        dialogs: MagicMock,
    ) -> None:
        refusal = PlaybackError("Failed to open audio stream: device busy")

        presenter.present_playing_failure(refusal)

        dialogs.show_error.assert_called_once_with(refusal, LANGUAGE_MANAGER[PLAYING_FAILURE_MESSAGE])

    def test_a_missing_output_still_reads_as_a_notice(
        self,
        presenter: PlaybackFailurePresenter,
        dialogs: MagicMock,
    ) -> None:
        presenter.present_playing_failure(NoOutputDeviceError("no device"))

        dialogs.show_info.assert_called_once()
        dialogs.show_error.assert_not_called()
