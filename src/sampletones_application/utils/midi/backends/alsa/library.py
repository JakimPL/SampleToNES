from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING, Final, Optional, Protocol, Tuple, Union

from sampletones_application.utils.midi.backends.protocol import MidiPort
from sampletones_shared.exceptions import MidiPortError

if TYPE_CHECKING:
    import alsa_midi

CLIENT_NAME: Final[str] = "SampleToNES"
INPUT_PORT_NAME: Final[str] = "input"
WAKE_PORT_NAME: Final[str] = "wake"
DISTRIBUTION_NAME: Final[str] = "alsa-midi"
LIBRARY_NAME: Final[str] = "ALSA sequencer"

Address = Tuple[int, int]


@dataclass(frozen=True)
class SequencerBytes:
    """A MIDI message the sequencer delivered to the input port, as its wire bytes."""

    data: bytes


@dataclass(frozen=True)
class SequencerLeft:
    """A client or one of its ports left the sequencer.

    Attributes:
        client: The client that left, or whose port left.
        port: The port that left, or ``None`` where the whole client left.
    """

    client: int
    port: Optional[int]


@dataclass(frozen=True)
class SequencerCut:
    """A subscription between two ports ended.

    Attributes:
        sender: The port the messages came from.
        destination: The port they went to.
    """

    sender: Address
    destination: Address


SequencerEvent = Union[SequencerBytes, SequencerLeft, SequencerCut]


class SequencerConnection(Protocol):
    """One client of the sequencer with an input port reading a source, read on one thread."""

    @property
    def address(self) -> Address:
        """Where the input port stands, which a wake is sent to."""

    def next_event(self) -> Optional[SequencerEvent]:
        """Waits for the next event, answering ``None`` for one that carries nothing the reader acts on.

        Raises:
            MidiPortError: If the sequencer fails to deliver.
        """

    def close(self) -> None: ...


class SequencerLibrary(Protocol):
    """What the backend asks of the ALSA sequencer: its inputs, a connection reading one, and a wake for it.

    It keeps the library to one module, so the backend's thread and its lifecycle are tested with a sequencer
    of the case's own on every platform.
    """

    def describe(self) -> str: ...

    def ports(self) -> Tuple[MidiPort, ...]: ...

    def connect(self, source: Address) -> SequencerConnection: ...

    def wake(self, address: Address) -> None:
        """Sends an event to ``address``, so a reader waiting there returns."""


class AlsaMidiLibrary:
    """The ALSA sequencer reached through ``alsa-midi``, which calls the system's own ALSA library.

    The system's library reads the system's configuration, which is what lets it find the sequencer. Every
    call opens a client of its own, so listing and waking leave the reader's client to the reader's thread.
    The library's failures arrive as ``MidiPortError``.
    """

    def describe(self) -> str:
        """Names the sequencer, the binding's version and the version of the system library it loaded."""
        import alsa_midi

        system = alsa_midi.ffi.string(alsa_midi.alsa.snd_asoundlib_version()).decode()
        return f"{LIBRARY_NAME} ({DISTRIBUTION_NAME} {version(DISTRIBUTION_NAME)}, ALSA {system})"

    def ports(self) -> Tuple[MidiPort, ...]:
        """Every port a keyboard can be read from, the loopback port among them, in the sequencer's order."""
        import alsa_midi

        try:
            client = alsa_midi.SequencerClient(CLIENT_NAME)
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer is unavailable: {error}") from error

        try:
            infos = client.list_ports(input=True)
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer failed to list its ports: {error}") from error
        finally:
            client.close()

        return tuple(MidiPort(name=info.name, address=(info.client_id, info.port_id)) for info in infos)

    def connect(self, source: Address) -> SequencerConnection:
        """A client whose input port reads ``source`` and hears the sequencer announce clients and ports leaving."""
        import alsa_midi

        try:
            client = alsa_midi.SequencerClient(CLIENT_NAME)
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer is unavailable: {error}") from error

        try:
            port = client.create_port(
                INPUT_PORT_NAME,
                caps=alsa_midi.WRITE_PORT,
                type=alsa_midi.PortType.MIDI_GENERIC | alsa_midi.PortType.APPLICATION,
            )
            port.connect_from(alsa_midi.Address(*source))
            port.connect_from(alsa_midi.SYSTEM_ANNOUNCE)
        except alsa_midi.Error as error:
            client.close()
            raise MidiPortError(f"The ALSA sequencer refused the port {source}: {error}") from error

        return AlsaMidiConnection(client, port)

    def wake(self, address: Address) -> None:
        import alsa_midi

        try:
            client = alsa_midi.SequencerClient(CLIENT_NAME)
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer is unavailable: {error}") from error

        try:
            port = client.create_port(WAKE_PORT_NAME, caps=alsa_midi.READ_PORT)
            client.event_output(alsa_midi.EchoEvent(), port=port, dest=alsa_midi.Address(*address))
            client.drain_output()
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer failed to reach {address}: {error}") from error
        finally:
            client.close()


class AlsaMidiConnection:
    """A client of the ALSA sequencer reading one source, waiting in the binding's poll until an event arrives.

    The binding deletes a port from the sequencer once its object is collected, so the connection keeps the input
    port for as long as it reads.
    """

    def __init__(self, client: "alsa_midi.SequencerClient", port: "alsa_midi.Port") -> None:
        self._client = client
        self._port = port

    @property
    def address(self) -> Address:
        return (self._client.client_id, self._port.port_id)

    def next_event(self) -> Optional[SequencerEvent]:
        import alsa_midi

        try:
            event = self._client.event_input(prefer_bytes=True)
        except alsa_midi.Error as error:
            raise MidiPortError(f"The ALSA sequencer failed to deliver: {error}") from error

        return _translated(event)

    def close(self) -> None:
        self._client.close()


def _translated(event: "alsa_midi.Event") -> Optional[SequencerEvent]:
    """The binding's event in the reader's terms, or ``None`` for one the reader acts on nothing for."""
    import alsa_midi

    match event:
        case alsa_midi.MidiBytesEvent():
            return SequencerBytes(data=bytes(event.midi_bytes))
        case alsa_midi.ClientExitEvent():
            return SequencerLeft(client=event.addr.client_id, port=None)
        case alsa_midi.PortExitEvent():
            return SequencerLeft(client=event.addr.client_id, port=event.addr.port_id)
        case alsa_midi.PortUnsubscribedEvent():
            return SequencerCut(
                sender=(event.connect_sender.client_id, event.connect_sender.port_id),
                destination=(event.connect_dest.client_id, event.connect_dest.port_id),
            )

    return None
