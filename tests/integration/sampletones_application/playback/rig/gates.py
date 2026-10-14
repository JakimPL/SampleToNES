import threading
from typing import Callable, Final, Generic, List, TypeVar, Union

from tests.suite.audio.machine import OpenCall, StreamCall

CallT = TypeVar("CallT", OpenCall, StreamCall)

HOLD_SECONDS: Final[float] = 10.0
ARRIVAL_SECONDS: Final[float] = 10.0


def every_call(_call: Union[OpenCall, StreamCall]) -> bool:
    return True


def from_write(index: int) -> Callable[[StreamCall], bool]:
    """Picks every write from the ``index``-th a stream takes onward, counted from zero."""
    return lambda call: call.writes >= index


class Gate(Generic[CallT]):
    """A point inside a device call where the calling thread waits until the case opens it.

    A case installs the gate as a machine hook, waits for a thread to arrive, acts while the thread stands
    there, and opens it. A gate the case leaves shut gives way after ``HOLD_SECONDS``, so a forgotten gate
    ends as a thread that outlived the case and not as a hang.
    """

    def __init__(self, *, holds: Callable[[CallT], bool]) -> None:
        self._holds = holds
        self._opened = threading.Event()
        self._arrived = threading.Event()
        self._lock = threading.Lock()
        self._held: List[CallT] = []

    def __call__(self, call: CallT) -> None:
        if self._opened.is_set() or not self._holds(call):
            return

        with self._lock:
            self._held.append(call)

        self._arrived.set()
        self._opened.wait(timeout=HOLD_SECONDS)

    @property
    def held(self) -> List[CallT]:
        """The calls the gate held, in the order they arrived."""
        with self._lock:
            return list(self._held)

    def wait_for_arrival(self) -> None:
        """Waits until a thread stands at the gate.

        Raises:
            AssertionError: If no thread arrives within ``ARRIVAL_SECONDS``.
        """
        assert self._arrived.wait(timeout=ARRIVAL_SECONDS), "no thread reached the gate"

    def open(self) -> None:
        self._opened.set()


class Fault(Generic[CallT]):
    """A device call that fails with ``OSError``, the way a device reports a failure, for the calls it picks."""

    def __init__(self, *, fails: Callable[[CallT], bool], message: str) -> None:
        self._fails = fails
        self._message = message

    def __call__(self, call: CallT) -> None:
        if self._fails(call):
            raise OSError(self._message)
