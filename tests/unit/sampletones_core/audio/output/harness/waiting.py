import time
from typing import Callable, Final

from .post import QueuedPost

WAIT_SECONDS: Final[float] = 10.0
POLL_SECONDS: Final[float] = 0.002


def wait_holding(condition: Callable[[], bool], *, what: str) -> None:
    """Waits until ``condition`` holds while every report stays queued for the owner.

    Raises:
        AssertionError: If ``WAIT_SECONDS`` pass first, naming ``what``.
    """
    deadline = time.monotonic() + WAIT_SECONDS
    while not condition():
        assert time.monotonic() < deadline, f"Waited in vain for {what}"
        time.sleep(POLL_SECONDS)


def wait_until(condition: Callable[[], bool], post: QueuedPost, *, what: str) -> None:
    """Drains the owner's queue until ``condition`` holds, which guards against a hang and measures nothing.

    Raises:
        AssertionError: If ``WAIT_SECONDS`` pass first, naming ``what``.
    """
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        post.drain()
        if condition():
            return

        assert time.monotonic() < deadline, f"Waited in vain for {what}"
        time.sleep(POLL_SECONDS)
