import threading
import time
from typing import Callable, Final, List, Tuple

import pytest

from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.clipboard.backends.x11.clipboard import (
    CLIPBOARD_ANSWER_SECONDS,
    X11TextClipboard,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from tests.suite.application import draw_frame
from tests.suite.base import BaseTestSuite

TEXT: Final[str] = "SampleToNES/1 order rows=1 positions=0..0\n03"
WAIT_LIMIT_SECONDS: Final[float] = 5.0
FRAME_PAUSE_SECONDS: Final[float] = 0.001


class HeldReader:
    """An owner that hands its text over once a case lets it, counting the transfers asked of it."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.release = threading.Event()
        self.threads: List[threading.Thread] = []
        self.deadlines: List[float] = []

    def read_text(self, seconds: float) -> str:
        self.threads.append(threading.current_thread())
        self.deadlines.append(seconds)
        self.release.wait(WAIT_LIMIT_SECONDS)
        return self.text


class FailingReader:
    """A reader whose transfer breaks, the way an unforeseen failure on the worker would."""

    def __init__(self) -> None:
        self.transfers: int = 0

    def read_text(self, seconds: float) -> str:
        self.transfers += 1
        raise RuntimeError("the transfer broke")


class Answers:
    """The texts a read was answered with, each beside the thread that answered it."""

    def __init__(self) -> None:
        self.received: List[Tuple[str, threading.Thread]] = []

    def __call__(self, text: str) -> None:
        self.received.append((text, threading.current_thread()))

    @property
    def texts(self) -> List[str]:
        return [text for text, _ in self.received]


def _draw_until(answered: Callable[[], bool]) -> None:
    """Draws frames until ``answered`` holds, the way the render loop drains between frames."""
    deadline = time.monotonic() + WAIT_LIMIT_SECONDS
    while not answered() and time.monotonic() < deadline:
        draw_frame()
        time.sleep(FRAME_PAUSE_SECONDS)


@pytest.mark.usefixtures("live_queue")
class TestAReadAnswersOnTheRenderThread(BaseTestSuite):
    """The owner is read on a worker, and its text reaches the thread that drains the queue."""

    def test_the_text_reaches_the_thread_draining_the_queue(self) -> None:
        reader = HeldReader(TEXT)
        answers = Answers()

        X11TextClipboard(reader).read(answers)
        reader.release.set()
        _draw_until(lambda: bool(answers.received))

        assert answers.received == [(TEXT, threading.current_thread())]
        assert reader.threads[0] is not threading.current_thread()

    def test_the_owner_has_the_answer_span_to_hand_its_text_over(self) -> None:
        reader = HeldReader(TEXT)
        answers = Answers()

        X11TextClipboard(reader).read(answers)
        reader.release.set()
        _draw_until(lambda: bool(answers.received))

        assert reader.deadlines == [CLIPBOARD_ANSWER_SECONDS]

    def test_the_frames_go_on_while_the_owner_is_silent(self) -> None:
        """This application's own window hands its text over as a frame polls its events."""
        reader = HeldReader(TEXT)
        answers = Answers()

        X11TextClipboard(reader).read(answers)
        for _ in range(3):
            draw_frame()

        assert answers.received == []

        reader.release.set()
        _draw_until(lambda: bool(answers.received))

        assert answers.texts == [TEXT]


@pytest.mark.usefixtures("live_queue")
class TestReadsShareATransfer(BaseTestSuite):
    """A burst of reads — a menu opening and a paste after it — asks the owner once."""

    def test_reads_asked_while_one_is_out_share_its_answer(self) -> None:
        reader = HeldReader(TEXT)
        clipboard = X11TextClipboard(reader)
        first, second = Answers(), Answers()

        clipboard.read(first)
        clipboard.read(second)
        reader.release.set()
        _draw_until(lambda: bool(first.received and second.received))

        assert (first.texts, second.texts) == ([TEXT], [TEXT])
        assert len(reader.threads) == 1

    def test_a_read_after_an_answer_asks_the_owner_again(self) -> None:
        """The clipboard changes between gestures, so each answered read leaves the next to ask."""
        reader = HeldReader(TEXT)
        reader.release.set()
        clipboard = X11TextClipboard(reader)
        first, second = Answers(), Answers()

        clipboard.read(first)
        _draw_until(lambda: bool(first.received))
        reader.text = "the text copied since"
        clipboard.read(second)
        _draw_until(lambda: bool(second.received))

        assert second.texts == ["the text copied since"]
        assert len(reader.threads) == 2

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
    def test_a_broken_transfer_answers_empty_and_the_next_read_asks_again(self) -> None:
        reader = FailingReader()
        clipboard = X11TextClipboard(reader)
        first, second = Answers(), Answers()

        clipboard.read(first)
        _draw_until(lambda: bool(first.received))
        clipboard.read(second)
        _draw_until(lambda: bool(second.received))

        assert (first.texts, second.texts) == ([""], [""])
        assert reader.transfers == 2


@pytest.mark.usefixtures("live_queue")
class TestShutdown(BaseTestSuite):
    def test_an_answer_on_its_way_at_shutdown_is_dropped(self) -> None:
        """The shutdown stops the queue before the context goes, so the answer reaches no widget."""
        reader = HeldReader(TEXT)
        answers = Answers()

        X11TextClipboard(reader).read(answers)
        CallbackQueue.stop()
        reader.release.set()
        SingleThreadExecutor.join_all(timeout=WAIT_LIMIT_SECONDS)
        draw_frame()

        assert answers.received == []
