import math
import threading
import time
from concurrent.futures import Future
from typing import Callable, Final, Protocol, TypeVar

AnswerT = TypeVar("AnswerT")
NEXT_DRAIN: Final[int] = 0
ONE_FRAME: Final[int] = 1
POLL_SECONDS: Final[float] = 0.05
REFERENCE_FRAME_RATE: Final[int] = 30


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

    def frames_drawn(self) -> int:
        """How many frames the render thread has drawn, read from any thread."""


class Deadline:
    """The end of a wait, which comes once its seconds have run and the render thread has drawn its frames.

    The frames are those a machine drawing ``REFERENCE_FRAME_RATE`` frames a second draws in the same seconds. A
    machine drawing more slowly answers each gesture in more seconds, so its waits stretch with its frames, and a
    wait fails on what the application did within them. A render thread that stops ends every wait.
    """

    def __init__(
        self,
        render_thread: RenderThread,
        *,
        seconds: float,
    ) -> None:
        self._render_thread = render_thread
        self.seconds = seconds
        self.frames = math.ceil(seconds * REFERENCE_FRAME_RATE)
        self._end = time.monotonic() + seconds
        self._last_frame = render_thread.frames_drawn() + self.frames

    def passed(self) -> bool:
        """Whether both the seconds and the frames of the wait have run, or the render thread stopped."""
        if not self._render_thread.is_running():
            return True

        return time.monotonic() >= self._end and self._render_thread.frames_drawn() >= self._last_frame


class Bridge:
    """The crossing a scenario takes to the render thread, where every reading and gesture happens.

    A question runs between two frames, so what it reads is one consistent frame. Its answer, or the
    exception it raised, comes back to the scenario's thread. Waiting is counted in frames drawn, and
    an expectation is read once a frame until it holds or its `Deadline` passes.
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
            ExpectationError: If no reading holds before the deadline of ``timeout`` seconds passes, naming the
                last one.
        """
        deadline = self.deadline(timeout)
        while True:
            value = reading()
            if holds(value):
                return value

            if deadline.passed():
                raise ExpectationError(
                    f"Expected {description} within {timeout} s and {deadline.frames} frames; "
                    f"the last reading was {value!r}"
                )

            self.frames(ONE_FRAME)

    def deadline(self, seconds: float) -> Deadline:
        """The deadline of a wait of ``seconds`` that starts now."""
        return Deadline(self._render_thread, seconds=seconds)

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
