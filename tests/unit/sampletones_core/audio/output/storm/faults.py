import random
import threading
import time
from typing import Final, Tuple

from tests.suite.audio.machine import MachineHooks, OpenCall, StreamCall

DELAY_CHANCE: Final[float] = 0.1
LONGEST_DELAY_SECONDS: Final[float] = 0.002
OPEN_FAILURE_CHANCE: Final[float] = 0.05
WRITE_FAILURE_CHANCE: Final[float] = 0.002
DRAIN_FAILURE_CHANCE: Final[float] = 0.05
CLOSE_FAILURE_CHANCE: Final[float] = 0.05


class DeviceFaults:
    """Delays and failures the storm gives the fake device's calls, drawn from the storm's seed.

    A call waits a moment now and then, and fails now and then while the faults are armed. A call decides
    whether it fails once its delay is over, so a call already waiting when the faults are disarmed answers.
    """

    def __init__(self, randomness: random.Random, hooks: MachineHooks) -> None:
        self._random = randomness
        self._lock = threading.Lock()
        self._armed: bool = True
        hooks.before_open = self._opening
        hooks.before_write = self._writing
        hooks.before_drain = self._draining
        hooks.before_close = self._closing

    def arm(self) -> None:
        with self._lock:
            self._armed = True

    def disarm(self) -> None:
        with self._lock:
            self._armed = False

    def _opening(self, _call: OpenCall) -> None:
        self._fault("open", OPEN_FAILURE_CHANCE)

    def _writing(self, _call: StreamCall) -> None:
        self._fault("write", WRITE_FAILURE_CHANCE)

    def _draining(self, _call: StreamCall) -> None:
        self._fault("drain", DRAIN_FAILURE_CHANCE)

    def _closing(self, _call: StreamCall) -> None:
        self._fault("close", CLOSE_FAILURE_CHANCE)

    def _fault(self, call: str, failure_chance: float) -> None:
        delay, fails = self._draw(failure_chance)
        time.sleep(delay)
        with self._lock:
            armed = self._armed

        if fails and armed:
            raise OSError(f"The storm failed the device's {call}")

    def _draw(self, failure_chance: float) -> Tuple[float, bool]:
        with self._lock:
            delayed = self._random.random() < DELAY_CHANCE
            delay = self._random.uniform(0.0, LONGEST_DELAY_SECONDS) if delayed else 0.0
            return delay, self._random.random() < failure_chance
