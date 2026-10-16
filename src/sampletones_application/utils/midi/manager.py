import threading
from typing import Callable, Optional, Protocol, Tuple

from sampletones_application.utils.midi.backends import MidiInputBackend, MidiPort
from sampletones_application.utils.midi.messages import (
    MidiAllNotesOff,
    MidiMessage,
    MidiPedal,
    parse_message,
)
from sampletones_shared.exceptions import MidiPortError

Clock = Callable[[], float]


class MidiListener(Protocol):
    """What hears the MIDI input: every message it plays something for, and the port going away.

    It hears a port's messages on the backend's thread, and the resets of a change on the thread making it.
    """

    def heard(self, message: MidiMessage, /) -> None: ...

    def lost(self, port_name: str, /) -> None:
        """Hears that the port read went away, as an unplugged keyboard does."""


class MidiInputManager:
    """The one MIDI input the application reads, connected by the name of its port.

    The session keeps a port's name, since names stay as devices come and go, and the manager finds the port by
    it in a fresh listing at each connection. A refresh is a disconnection, a listing and a connection by the
    same name, which every backend serves alike.

    A device keeps what is played while nothing reads it and sends it all as a port opens, so the messages
    arriving within ``settle_seconds`` of an opening are dropped, and a burst of old notes stays silent.

    Whenever the keys stop reaching the listener, as the port changes, goes away or is let go, the listener
    hears every key let go and the pedal come up, so no note hangs on a key whose release will never arrive.

    Its operations run one at a time under a lock of their own, so a startup thread and the render thread may
    both drive it, and the backend calls its sink from a thread of its own.
    """

    def __init__(
        self,
        backend: MidiInputBackend,
        *,
        listener: MidiListener,
        settle_seconds: float,
        clock: Clock,
    ) -> None:
        """Holds the backend and who hears it.

        Args:
            backend: The MIDI library the input is read through.
            listener: What hears the messages and the port going away.
            settle_seconds: How long after a port opens its messages are dropped.
            clock: The seconds the settling is measured in, increasing.
        """
        self._backend = backend
        self._listener = listener
        self._settle_seconds = settle_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._operations = threading.RLock()
        self._connection: Optional[_Connection] = None

    @property
    def port_name(self) -> Optional[str]:
        """The port read, or ``None`` while none is."""
        with self._lock:
            return None if self._connection is None else self._connection.name

    def describe(self) -> str:
        """The library the input is read through, loading it.

        Raises:
            MidiPortError: If the library fails to load.
        """
        with self._operations:
            return self._backend.describe()

    def ports(self) -> Tuple[str, ...]:
        """The names of the inputs as they stand now.

        Raises:
            MidiPortError: If the library fails to list them.
        """
        with self._operations:
            return tuple(port.name for port in self._backend.ports())

    def connect(self, name: str) -> bool:
        """Reads the port named ``name`` from now on, letting the port read before go.

        Returns:
            bool: Whether a port of that name stands among the inputs now, and was opened.

        Raises:
            MidiPortError: If the library fails to list the inputs or to open the port.
        """
        with self._operations:
            self.disconnect()
            return self._open_named(name, self._backend.ports())

    def refresh(self) -> Tuple[str, ...]:
        """Lists the inputs again and reads the port read before by its name, where it still stands.

        Returns:
            Tuple[str, ...]: The names of the inputs as they stand now.

        Raises:
            MidiPortError: If the library fails to list the inputs or to open the port again.
        """
        with self._operations:
            name = self.port_name
            self.disconnect()
            ports = self._backend.ports()
            if name is not None:
                self._open_named(name, ports)

            return tuple(port.name for port in ports)

    def disconnect(self) -> None:
        """Lets the port read go, and lets every key go with it."""
        with self._operations:
            with self._lock:
                connection, self._connection = self._connection, None

            self._backend.close()
            if connection is not None:
                self._release_keys()

    def _open_named(self, name: str, ports: Tuple[MidiPort, ...]) -> bool:
        port = next((listed for listed in ports if listed.name == name), None)
        if port is None:
            return False

        connection = _Connection(
            name,
            listener=self._listener,
            settled_at=self._clock() + self._settle_seconds,
            clock=self._clock,
            on_lost=self._lost,
        )
        with self._lock:
            self._connection = connection

        try:
            self._backend.open(port, connection)
        except MidiPortError:
            with self._lock:
                if self._connection is connection:
                    self._connection = None

            raise

        return True

    def _lost(self, connection: "_Connection") -> None:
        """Hears a port going away on the backend's thread: every key lets go, and the listener hears the loss."""
        with self._lock:
            if self._connection is not connection:
                return

            self._connection = None

        self._release_keys()
        self._listener.lost(connection.name)

    def _release_keys(self) -> None:
        self._listener.heard(MidiAllNotesOff())
        self._listener.heard(MidiPedal(down=False))


class _Connection:
    """One opening of one port, the sink its backend calls: it drops what arrives while the port settles, and
    reads the rest as messages for the listener."""

    def __init__(
        self,
        name: str,
        *,
        listener: MidiListener,
        settled_at: float,
        clock: Clock,
        on_lost: Callable[["_Connection"], None],
    ) -> None:
        self.name = name
        self._listener = listener
        self._settled_at = settled_at
        self._clock = clock
        self._on_lost = on_lost

    def received(self, message: bytes) -> None:
        if self._clock() < self._settled_at:
            return

        parsed = parse_message(message)
        if parsed is not None:
            self._listener.heard(parsed)

    def lost(self) -> None:
        self._on_lost(self)
