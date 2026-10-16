import contextlib
import threading
import time
from typing import Callable, Final, Iterator, List, Optional, Set

import pytest

from .reports import Wait

HELPER_PREFIX: Final[str] = "PlaybackRigHelper"

Join = Callable[[threading.Thread, Optional[float]], None]


class ThreadWatch:
    """The threads a case starts, the joins the render thread makes on them, and what escapes them.

    A thread counts as an audio thread when the case started it, leaving out timers and the rig's own
    helpers, since the watch finds audio threads by what is new. A join counts as a wait when the render
    thread makes it on an audio thread while a gesture other than the teardown runs.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._render_thread = threading.current_thread()
        self._known: Set[threading.Thread] = set(threading.enumerate())
        self._lock = threading.Lock()
        self._watching: bool = False
        self._waits: List[Wait] = []
        self._escaped: List[BaseException] = []
        monkeypatch.setattr(threading, "excepthook", self._escape)
        monkeypatch.setattr(threading.Thread, "join", self._spying(threading.Thread.join))

    @property
    def waits(self) -> List[Wait]:
        with self._lock:
            return list(self._waits)

    @property
    def escaped(self) -> List[BaseException]:
        with self._lock:
            return list(self._escaped)

    def audio_threads(self) -> List[threading.Thread]:
        """The audio threads alive now."""
        return [thread for thread in threading.enumerate() if self._is_audio(thread) and thread.is_alive()]

    def join_audio_threads(self, *, deadline_seconds: float) -> List[threading.Thread]:
        """Waits up to the deadline for every audio thread to end, and answers the ones still alive."""
        deadline = time.monotonic() + deadline_seconds
        for thread in self.audio_threads():
            thread.join(timeout=max(0.0, deadline - time.monotonic()))

        return self.audio_threads()

    @contextlib.contextmanager
    def watching_waits(self) -> Iterator[None]:
        """Counts the joins the render thread makes on audio threads while the block runs."""
        with self._lock:
            watching, self._watching = self._watching, True

        try:
            yield
        finally:
            with self._lock:
                self._watching = watching

    def _is_audio(self, thread: threading.Thread) -> bool:
        return (
            thread not in self._known
            and not isinstance(thread, threading.Timer)
            and not thread.name.startswith(HELPER_PREFIX)
        )

    def _spying(self, join: Join) -> Join:
        def spying_join(thread: threading.Thread, timeout: Optional[float] = None) -> None:
            if threading.current_thread() is self._render_thread and self._is_audio(thread):
                with self._lock:
                    if self._watching:
                        self._waits.append(Wait(joined=thread.name))

            join(thread, timeout)

        return spying_join

    def _escape(self, arguments: threading.ExceptHookArgs) -> None:
        if arguments.exc_value is not None:
            with self._lock:
                self._escaped.append(arguments.exc_value)
