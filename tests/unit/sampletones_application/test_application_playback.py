import threading
from typing import Final, Iterator, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.application import Application
from sampletones_application.coordinators.playback.failures import PlaybackFailurePresenter
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.render_thread import claim_render_thread, release_render_thread
from sampletones_shared.exceptions import PlaybackError
from tests.suite.language import FakeLanguageManager

FAILURE_MESSAGE_KEY: Final[str] = "global.dialog.message.audio_playback_error"


class _PresenterRecorder:
    """Notes the thread each failure is presented on, which is where its dialog is built."""

    def __init__(self) -> None:
        self.presented: List[Tuple[int, Exception, Optional[str]]] = []

    def present(self, exception: Exception, *, message: Optional[str]) -> None:
        self.presented.append((threading.get_ident(), exception, message))


@pytest.fixture(name="presenter")
def presenter_fixture() -> _PresenterRecorder:
    return _PresenterRecorder()


@pytest.fixture(name="application")
def application_fixture(presenter: _PresenterRecorder) -> Application:
    application = Application.__new__(Application)
    application._playback_failures = MagicMock(spec=PlaybackFailurePresenter)
    application._playback_failures.present.side_effect = presenter.present
    application.language_manager = FakeLanguageManager()
    return application


@pytest.fixture(name="drawing")
def drawing_fixture() -> Iterator[None]:
    """A run drawing its frames on this thread, over a queue live enough to drain what reaches it."""
    CallbackQueue.start()
    claim_render_thread()
    yield
    release_render_thread()
    CallbackQueue.stop()
    CallbackQueue.start()


class TestAPlaybackTheDeviceRefused:
    """A stream that fails to open is reported where the interface is drawn, whichever thread heard of it."""

    @pytest.mark.usefixtures("drawing")
    def test_a_report_from_the_playing_thread_waits_for_the_render_thread(
        self,
        application: Application,
        presenter: _PresenterRecorder,
    ) -> None:
        failure = PlaybackError("Failed to open audio stream")
        worker = threading.Thread(target=application._on_playback_error, args=(failure,))
        worker.start()
        worker.join()

        assert presenter.presented == []
        CallbackQueue.process(1.0)

        assert presenter.presented == [(threading.get_ident(), failure, FAILURE_MESSAGE_KEY)]

    @pytest.mark.usefixtures("drawing")
    def test_a_report_on_the_render_thread_is_presented_at_once(
        self,
        application: Application,
        presenter: _PresenterRecorder,
    ) -> None:
        failure = PlaybackError("Failed to open audio stream")

        application._on_playback_error(failure)

        assert presenter.presented == [(threading.get_ident(), failure, FAILURE_MESSAGE_KEY)]
