import time
from pathlib import Path
from typing import Final

RELEASE_POLL_SECONDS: Final[float] = 0.01
RELEASE_TIMEOUT_SECONDS: Final[float] = 30.0


def wait_for_release(release_path: Path) -> None:
    """Holds a worker until the test that started it writes ``release_path``.

    A test asserting that a reading arrived while work was still under way has to know the work
    was still under way when it looked, and a task quick enough to finish first would leave that
    assertion resting on the scheduler. Holding the task where the test wants to see it settles
    the question.

    The wait gives up after ``RELEASE_TIMEOUT_SECONDS`` and lets the task finish, so a test that
    never releases it fails on its own assertion rather than holding a run open.

    Args:
        release_path: The file whose appearance lets the worker carry on.
    """
    deadline = time.monotonic() + RELEASE_TIMEOUT_SECONDS
    while not release_path.exists() and time.monotonic() < deadline:
        time.sleep(RELEASE_POLL_SECONDS)
