import queue
import threading
from typing import Final, List, Optional, Tuple, Union

import pytest

import sampletones_application.application as application_module
from sampletones_application.utils.midi.backends import MidiPort, MidiSink
from sampletones_shared.exceptions import MidiPortError

THREAD_NAME: Final[str] = "FakeMidi"
SYSTEM_EXCLUSIVE: Final[int] = 0xF0
BACKEND_FAILURE: Final[str] = "The fake MIDI library failed"

Delivery = Union[bytes, "_Lost", "_Stop"]


class _Lost:
    """The open port went away."""


class _Stop:
    """The open port is let go."""


class ScriptedMidiInput:
    """The MIDI library a scenario stands behind: ports it plugs in, plays and unplugs, delivered from a thread of
    its own.

    It keeps the protocol a library backend keeps, so the application meets here what it meets on a machine with
    a keyboard, and a scenario reaches the MIDI library of no machine it runs on.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._offered: List[str] = []
        self._open_name: Optional[str] = None
        self._deliveries: "Optional[queue.Queue[Delivery]]" = None
        self._thread: Optional[threading.Thread] = None
        self.failing: bool = False
        self.opened: List[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stands in for the MIDI library the application selects as it starts."""
        monkeypatch.setattr(application_module, "select_midi_backend", lambda: self)

    def describe(self) -> str:
        self._check()
        return "fake MIDI backend"

    def ports(self) -> Tuple[MidiPort, ...]:
        self._check()
        with self._lock:
            return tuple(MidiPort(name=name, address=(index,)) for index, name in enumerate(self._offered))

    def open(self, port: MidiPort, sink: MidiSink) -> None:
        self.close()
        self._check()
        with self._lock:
            if port.name not in self._offered:
                raise MidiPortError(f"The port {port.name!r} is gone")

            deliveries: "queue.Queue[Delivery]" = queue.Queue()
            self._open_name, self._deliveries = port.name, deliveries
            self.opened.append(port.name)

        self._thread = threading.Thread(
            target=self._deliver,
            args=(deliveries, sink),
            name=THREAD_NAME,
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        with self._lock:
            deliveries, thread = self._deliveries, self._thread
            self._open_name, self._deliveries, self._thread = None, None, None

        if deliveries is not None and thread is not None:
            deliveries.put(_Stop())
            if thread is not threading.current_thread():
                thread.join()

    def offer(self, name: str) -> None:
        with self._lock:
            self._offered.append(name)

    def play(self, name: str, message: bytes) -> None:
        with self._lock:
            if self._open_name == name and self._deliveries is not None:
                self._deliveries.put(message)

    def drain(self) -> None:
        """Waits until the open port's sink has taken every message played so far."""
        with self._lock:
            deliveries = self._deliveries

        if deliveries is not None:
            deliveries.join()

    def unplug(self, name: str) -> None:
        with self._lock:
            self._offered.remove(name)
            if self._open_name == name and self._deliveries is not None:
                self._deliveries.put(_Lost())

    def _deliver(self, deliveries: "queue.Queue[Delivery]", sink: MidiSink) -> None:
        while True:
            delivery = deliveries.get()
            try:
                match delivery:
                    case bytes() if delivery[:1] != bytes((SYSTEM_EXCLUSIVE,)):
                        sink.received(delivery)
                    case _Lost():
                        sink.lost()
                        return
                    case _Stop():
                        return
            finally:
                deliveries.task_done()

    def _check(self) -> None:
        if self.failing:
            raise MidiPortError(BACKEND_FAILURE)
