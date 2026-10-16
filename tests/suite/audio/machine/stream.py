import threading
from typing import Callable, Final, Optional

import numpy as np

from tests.suite.audio.pacing import Pacing
from tests.suite.audio.timeline import Closed, Drained, Timeline, Violation, ViolationKind, Written

from .calls import StreamCall
from .hooks import MachineHooks
from .messages import STREAM_CLOSED

SAMPLE_BYTES: Final[int] = np.dtype(np.float32).itemsize


class FakeOutputStream:
    """A blocking stream on the fake device, paced by the machine's clock and recorded on its timeline.

    A write counts as in progress from the moment it begins, its hook included, so a close another thread
    makes meanwhile is recorded as one. A close lets the device go even where it fails, as a device frees a
    stream it reports an error closing.
    """

    def __init__(
        self,
        *,
        stream: int,
        sample_rate: int,
        pacing: Pacing,
        timeline: Timeline,
        hooks: MachineHooks,
        on_closed: Callable[[int], None],
    ) -> None:
        self.stream = stream
        self._sample_rate = sample_rate
        self._pacing = pacing
        self._timeline = timeline
        self._hooks = hooks
        self._on_closed = on_closed
        self._lock = threading.Lock()
        self._closed: bool = False
        self._writes: int = 0
        self._writing: Optional[str] = None

    def write(self, data: bytes) -> None:
        thread = threading.current_thread().name
        frames = len(data) // SAMPLE_BYTES
        with self._lock:
            writes = self._writes
            closed = self._closed
            if not closed:
                self._writing = thread

        if closed:
            self._violate(ViolationKind.WRITE_AFTER_CLOSE, thread)
            raise OSError(STREAM_CLOSED)

        try:
            self._hooks.writing(StreamCall(stream=self.stream, writes=writes, frames=frames))
            self._pacing.admit(self.stream, frames, self._sample_rate)
        finally:
            with self._lock:
                self._writing = None
                closed = self._closed
                self._writes += 1

        if closed:
            raise OSError(STREAM_CLOSED)

        samples = np.frombuffer(data, dtype=np.float32).copy()
        self._timeline.record(Written(stream=self.stream, samples=samples, thread=thread))

    def drain(self) -> None:
        thread = threading.current_thread().name
        with self._lock:
            closed = self._closed
            writes = self._writes

        if closed:
            self._violate(ViolationKind.DRAIN_AFTER_CLOSE, thread)
            raise OSError(STREAM_CLOSED)

        self._hooks.draining(StreamCall(stream=self.stream, writes=writes, frames=0))
        self._pacing.drain(self.stream)
        self._timeline.record(Drained(stream=self.stream, thread=thread))

    def close(self) -> None:
        thread = threading.current_thread().name
        with self._lock:
            closed, self._closed = self._closed, True
            writing = self._writing
            writes = self._writes

        if closed:
            self._violate(ViolationKind.CLOSE_TWICE, thread)
            return

        if writing is not None and writing != thread:
            self._violate(ViolationKind.CLOSE_DURING_WRITE, thread)

        try:
            self._hooks.closing(StreamCall(stream=self.stream, writes=writes, frames=0))
        finally:
            discarded = self._pacing.discard(self.stream)
            self._on_closed(self.stream)
            self._timeline.record(Closed(stream=self.stream, discarded=discarded, thread=thread))

    def _violate(self, kind: ViolationKind, thread: str) -> None:
        self._timeline.record(Violation(kind=kind, stream=self.stream, thread=thread))
