import threading
from typing import Final, Iterator, List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.utils.callbacks.failures import FailurePresenter, UnhandledFailures

FAILURES_LOGGER: Final[str] = "sampletones_application.utils.callbacks.failures.logger"
ORIGIN: Final[str] = "Error in the place it escaped"
THREAD_TIMEOUT: Final[float] = 5.0


class Posts:
    """What the channel hands to the render thread, held until the case drains it."""

    def __init__(self) -> None:
        self.held: List[Tuple[FailurePresenter, Exception]] = []
        self._lock = threading.Lock()

    def post(self, presenter: FailurePresenter, exception: Exception) -> None:
        with self._lock:
            self.held.append((presenter, exception))

    def drain(self) -> None:
        """Runs what was posted, the way the render loop's drain does."""
        with self._lock:
            held, self.held = self.held, []

        for presenter, exception in held:
            presenter(exception)


@pytest.fixture
def posts() -> Posts:
    return Posts()


@pytest.fixture
def presented() -> List[Exception]:
    return []


@pytest.fixture
def attached(posts: Posts, presented: List[Exception]) -> None:
    UnhandledFailures.attach(presented.append, post=posts.post)


class HookInPlace:
    """The thread hook a case puts in place before attaching, noting what each escape reached it with."""

    def __init__(self) -> None:
        self.reached: List[type] = []

    def __call__(self, arguments: threading.ExceptHookArgs) -> None:
        self.reached.append(arguments.exc_type)


@pytest.fixture
def hook_in_place(monkeypatch: pytest.MonkeyPatch) -> Iterator[HookInPlace]:
    """A hook of the case's own in place of the thread hook, detached from before the hook goes back."""
    hook = HookInPlace()
    monkeypatch.setattr(threading, "excepthook", hook)
    yield hook
    UnhandledFailures.detach()


@pytest.fixture
def logger() -> Iterator[MagicMock]:
    with patch(FAILURES_LOGGER) as logger:
        yield logger


def escape_on_a_thread(exception: BaseException) -> None:
    """Runs a thread that lets ``exception`` escape, and waits for it to end."""

    def target() -> None:
        raise exception

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(THREAD_TIMEOUT)


class TestReporting:
    """A failure is logged where it escaped, and the reader is shown it from the render thread."""

    @pytest.mark.usefixtures("attached")
    def test_a_report_is_logged_and_shown_once_drained(
        self,
        posts: Posts,
        presented: List[Exception],
        logger: MagicMock,
    ) -> None:
        failure = RuntimeError("it went wrong")

        UnhandledFailures.report(failure, ORIGIN)
        assert presented == []
        posts.drain()

        logger.error_with_traceback.assert_called_once_with(failure, ORIGIN)
        assert presented == [failure]

    def test_a_report_with_nothing_attached_is_logged_alone(self, posts: Posts, logger: MagicMock) -> None:
        failure = RuntimeError("it went wrong")

        UnhandledFailures.report(failure, ORIGIN)

        logger.error_with_traceback.assert_called_once_with(failure, ORIGIN)
        assert posts.held == []

    @pytest.mark.usefixtures("attached")
    def test_a_report_after_the_detachment_is_logged_alone(self, posts: Posts, logger: MagicMock) -> None:
        UnhandledFailures.detach()

        UnhandledFailures.report(RuntimeError("it went wrong"), ORIGIN)

        logger.error_with_traceback.assert_called_once()
        assert posts.held == []

    @pytest.mark.usefixtures("attached")
    def test_a_report_drained_after_the_detachment_shows_nothing(
        self,
        posts: Posts,
        presented: List[Exception],
    ) -> None:
        UnhandledFailures.report(RuntimeError("it went wrong"), ORIGIN)
        UnhandledFailures.detach()

        posts.drain()

        assert presented == []

    def test_a_presenter_that_fails_is_logged_and_posts_nothing_more(self, posts: Posts, logger: MagicMock) -> None:
        breakage = RuntimeError("the report broke")

        def failing(_: Exception) -> None:
            raise breakage

        UnhandledFailures.attach(failing, post=posts.post)
        UnhandledFailures.report(RuntimeError("it went wrong"), ORIGIN)

        posts.drain()

        assert logger.error_with_traceback.call_args_list[-1].args[0] is breakage
        assert posts.held == []


class TestTheThreadHook:
    """A thread letting an ``Exception`` escape reports it, and anything else reaches the hook in place."""

    @pytest.mark.usefixtures("attached")
    def test_an_escaping_exception_is_reported(self, posts: Posts, presented: List[Exception]) -> None:
        failure = RuntimeError("the worker went wrong")

        escape_on_a_thread(failure)
        posts.drain()

        assert presented == [failure]

    def test_a_system_exit_reaches_the_hook_in_place(self, hook_in_place: HookInPlace, posts: Posts) -> None:
        UnhandledFailures.attach(lambda _: None, post=posts.post)

        escape_on_a_thread(SystemExit(0))

        assert hook_in_place.reached == [SystemExit]
        assert posts.held == []

    def test_the_detachment_puts_back_the_hook_in_place(self, hook_in_place: HookInPlace, posts: Posts) -> None:
        UnhandledFailures.attach(lambda _: None, post=posts.post)
        assert threading.excepthook is not hook_in_place

        UnhandledFailures.detach()

        assert threading.excepthook is hook_in_place

    def test_attaching_again_keeps_the_hook_found_first(self, hook_in_place: HookInPlace, posts: Posts) -> None:
        UnhandledFailures.attach(lambda _: None, post=posts.post)
        UnhandledFailures.attach(lambda _: None, post=posts.post)

        UnhandledFailures.detach()

        assert threading.excepthook is hook_in_place
