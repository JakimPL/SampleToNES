import queue
import threading
from typing import Dict, Final, List, Optional, Tuple, Union

from sampletones_application.utils.midi.backends import MidiPort
from sampletones_application.utils.midi.backends.alsa.library import (
    Address,
    SequencerBytes,
    SequencerCut,
    SequencerEvent,
    SequencerLeft,
)
from sampletones_shared.exceptions import MidiPortError

FIRST_CLIENT: Final[int] = 128
DEVICE_PORT: Final[int] = 0
READER_CLIENT: Final[int] = 200
SEQUENCER_FAILURE: Final[str] = "The sequencer failed"

Delivery = Union[Optional[SequencerEvent], MidiPortError]


class FakeConnection:
    """A reader's client on the fake sequencer: what it is sent waits in line until the reader takes it."""

    def __init__(self, sequencer: "FakeSequencer", *, source: Address, address: Address) -> None:
        self.source = source
        self._sequencer = sequencer
        self._address = address
        self._deliveries: "queue.Queue[Delivery]" = queue.Queue()
        self.closed: bool = False

    @property
    def address(self) -> Address:
        return self._address

    def next_event(self) -> Optional[SequencerEvent]:
        delivery = self._deliveries.get()
        if isinstance(delivery, MidiPortError):
            raise delivery

        return delivery

    def close(self) -> None:
        self.closed = True
        self._sequencer.forget(self)

    def deliver(self, delivery: Delivery) -> None:
        self._deliveries.put(delivery)


class FakeSequencer:
    """The ALSA sequencer as the backend reaches it, with keyboards a case plugs in, plays and unplugs.

    Each keyboard is a client of its own with one port. Every reader hears the sequencer announce a client
    leaving, as a reader subscribed to the announcements does, and a wake reaches the reader it names.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ports: Dict[str, Address] = {}
        self._connections: List[FakeConnection] = []
        self._next_client = FIRST_CLIENT
        self._next_reader = READER_CLIENT
        self.failing: bool = False
        self.wakes: int = 0

    @property
    def connections(self) -> Tuple[FakeConnection, ...]:
        with self._lock:
            return tuple(self._connections)

    def offer(self, name: str) -> Address:
        with self._lock:
            address = (self._next_client, DEVICE_PORT)
            self._next_client += 1
            self._ports[name] = address
            return address

    def describe(self) -> str:
        return "fake sequencer"

    def ports(self) -> Tuple[MidiPort, ...]:
        self._check()
        with self._lock:
            return tuple(MidiPort(name=name, address=address) for name, address in self._ports.items())

    def connect(self, source: Address) -> FakeConnection:
        self._check()
        with self._lock:
            if source not in self._ports.values():
                raise MidiPortError(f"No port stands at {source}")

            connection = FakeConnection(self, source=source, address=(self._next_reader, DEVICE_PORT))
            self._next_reader += 1
            self._connections.append(connection)
            return connection

    def wake(self, address: Address) -> None:
        self._check()
        self.wakes += 1
        for connection in self.connections:
            if connection.address == address:
                connection.deliver(None)

    def play(self, name: str, message: bytes) -> None:
        """Sends ``message`` from the keyboard named ``name`` to every reader subscribed to it."""
        address = self._ports[name]
        for connection in self.connections:
            if connection.source == address:
                connection.deliver(SequencerBytes(data=message))

    def unplug(self, name: str) -> None:
        """The keyboard named ``name`` leaves the sequencer, which every reader hears announced."""
        with self._lock:
            client, _ = self._ports.pop(name)

        self.announce(SequencerLeft(client=client, port=None))

    def announce(self, event: Union[SequencerLeft, SequencerCut]) -> None:
        for connection in self.connections:
            connection.deliver(event)

    def break_delivery(self) -> None:
        """Every reader's next wait fails, as a sequencer failing to deliver does."""
        for connection in self.connections:
            connection.deliver(MidiPortError(SEQUENCER_FAILURE))

    def forget(self, connection: FakeConnection) -> None:
        with self._lock:
            self._connections.remove(connection)

    def _check(self) -> None:
        if self.failing:
            raise MidiPortError(SEQUENCER_FAILURE)
