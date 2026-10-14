import threading
import time
from typing import Dict


class TickerPacing:
    """A device that plays at its rate times ``speed``, holding ``buffer_seconds`` of audio ahead.

    A write returns once what it adds fits in the device's buffer, and a drain once the device has
    played everything, as a sound card does at a faster pace. A case reading outcomes runs quickly
    on it, and the writer still meets a device that holds it back.
    """

    def __init__(self, *, speed: float, buffer_seconds: float) -> None:
        self._speed = speed
        self._buffer_seconds = buffer_seconds
        self._lock = threading.Lock()
        self._played_out_at: Dict[int, float] = {}
        self._rates: Dict[int, int] = {}
        self._discarded: Dict[int, threading.Event] = {}

    def admit(self, stream: int, frames: int, sample_rate: int) -> None:
        now = time.monotonic()
        with self._lock:
            played_out_at = max(self._played_out_at.get(stream, now), now) + frames / (sample_rate * self._speed)
            self._played_out_at[stream] = played_out_at
            self._rates[stream] = sample_rate
            discarded = self._discarded.setdefault(stream, threading.Event())

        discarded.wait(timeout=max(0.0, played_out_at - self._buffer_seconds / self._speed - now))

    def drain(self, stream: int) -> None:
        with self._lock:
            played_out_at = self._played_out_at.get(stream, time.monotonic())
            discarded = self._discarded.setdefault(stream, threading.Event())

        discarded.wait(timeout=max(0.0, played_out_at - time.monotonic()))

    def discard(self, stream: int) -> int:
        now = time.monotonic()
        with self._lock:
            played_out_at = self._played_out_at.pop(stream, now)
            sample_rate = self._rates.pop(stream, 0)
            self._discarded.setdefault(stream, threading.Event()).set()

        return max(0, round((played_out_at - now) * sample_rate * self._speed))
