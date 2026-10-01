import threading
import time
from concurrent.futures import Future
from typing import Callable, Final, Protocol, TypeVar

AnswerT = TypeVar("AnswerT")

NEXT_DRAIN: Final[int] = 0
ONE_FRAME: Final[int] = 1
POLL_SECONDS: Final[float] = 0.05


class RenderThreadTimeoutError(AssertionError):
    """Raised when the render thread leaves a question unanswered while it still runs."""


class RenderThreadStoppedError(AssertionError):
    """Raised when the application stops drawing before it answers a scenario's question."""


class ExpectationError(AssertionError):
    """Raised when what a scenario expects never holds within its time."""


class RenderThread(Protocol):
    """The thread an application's DearPyGui context belongs to, reached from a scenario's own thread.

    The application under test says how work reaches it, which is the one thing this layer asks of
    the application.
    """

    def post(
        self,
        task: Callable[[], None],
        *,
        frames: int,
    ) -> None:
        """Runs ``task`` on the render thread once ``frames`` more frames have been drawn."""

    def is_running(self) -> bool:
        """Whether the render thread still draws frames, and so still runs what is posted to it."""


class Bridge:
    """The crossing a scenario takes to the render thread, where every reading and gesture happens.

    A question runs between two frames, so what it reads is one consistent frame. Its answer, or the
    exception it raised, comes back to the scenario's thread. Waiting is counted in frames drawn, and
    an expectation is read once a frame until it holds or its time runs out.
    """

    def __init__(
        self,
        render_thread: RenderThread,
        *,
        answer_timeout: float,
    ) -> None:
        self._render_thread = render_thread
        self._answer_timeout = answer_timeout

    def ask(self, question: Callable[[], AnswerT]) -> AnswerT:
        """Runs ``question`` on the render thread and returns what it answered.

        Raises:
            RenderThreadTimeoutError: If the render thread leaves the question unanswered.
            RenderThreadStoppedError: If the application stops before answering.
        """
        answer: Future[AnswerT] = Future()
        answered = threading.Event()

        def task() -> None:
            try:
                answer.set_result(question())
            except BaseException as error:  # pylint: disable=broad-exception-caught
                answer.set_exception(error)
            finally:
                answered.set()

        self._render_thread.post(task, frames=NEXT_DRAIN)
        self._wait(answered, what="a question")
        return answer.result()

    def frames(self, count: int) -> None:
        """Waits until ``count`` more frames have been drawn.

        Raises:
            RenderThreadTimeoutError: If the frames stop arriving.
            RenderThreadStoppedError: If the application stops before they are drawn.
        """
        drawn = threading.Event()
        self._render_thread.post(drawn.set, frames=count)
        self._wait(drawn, what=f"{count} frames")

    def expect(
        self,
        reading: Callable[[], AnswerT],
        holds: Callable[[AnswerT], bool],
        *,
        description: str,
        timeout: float,
    ) -> AnswerT:
        """Takes ``reading`` once a frame until ``holds`` accepts it, and returns that reading.

        ``reading`` runs on the caller's thread, so it asks the render thread for what it reads and
        may combine several answers.

        Raises:
            ExpectationError: If no reading within ``timeout`` seconds holds, naming the last one.
        """
        deadline = time.monotonic() + timeout
        while True:
            value = reading()
            if holds(value):
                return value

            if time.monotonic() >= deadline:
                raise ExpectationError(f"Expected {description} within {timeout} s; the last reading was {value!r}")

            self.frames(ONE_FRAME)

    def _wait(
        self,
        event: threading.Event,
        *,
        what: str,
    ) -> None:
        deadline = time.monotonic() + self._answer_timeout
        while not event.wait(POLL_SECONDS):
            if not self._render_thread.is_running() and not event.is_set():
                raise RenderThreadStoppedError(f"The application stopped before {what} came back")
            if time.monotonic() >= deadline:
                raise RenderThreadTimeoutError(f"The render thread left {what} unanswered for {self._answer_timeout} s")
