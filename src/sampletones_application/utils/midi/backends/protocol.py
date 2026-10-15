from dataclasses import dataclass
from typing import Protocol, Tuple


@dataclass(frozen=True)
class MidiPort:
    """One MIDI input as a backend lists it.

    The reader picks a port by its name, and the session keeps the name, since it is what stays the same as
    devices come and go. The address is where the backend finds the port, and only that backend reads it.

    Attributes:
        name: The name the port goes by.
        address: Where the backend finds the port, as it stood at the listing that named it.
    """

    name: str
    address: Tuple[int, ...]


class MidiSink(Protocol):
    """What hears an open port, from a thread the backend owns."""

    def received(self, message: bytes, /) -> None:
        """Takes one complete MIDI 1.0 message, status byte first."""

    def lost(self) -> None:
        """Hears that the port went away; nothing more arrives from it."""


class MidiInputBackend(Protocol):
    """A MIDI library as the application reaches it: the inputs it lists, and the one port it reads.

    The seam carries what every MIDI library offers, so a library is replaced by one backend of its own:

    - ``ports`` lists the inputs as they stand now, and a port left open goes on delivering.
    - ``open`` reads one port at a time, and opening another closes the one open before. The backend calls the
      sink from a thread it owns, one call at a time, in the order the messages arrived. Each message is
      complete, running status resolved, and system exclusive messages stay behind. A port that goes away is
      told once, and nothing more arrives from it.
    - ``close`` returns once the sink hears nothing more, and the sink may call it from its own call. Closing with no
      port open does nothing.
    - Messages act on arrival, so no timestamp crosses, and nothing is sent to a device.
    - A library's failure arrives as ``MidiPortError``, so no library's exception crosses either.
    """

    def describe(self) -> str:
        """The library the backend reads through and its version, loading the library as reading a port does.

        Raises:
            MidiPortError: If the library fails to load.
        """

    def ports(self) -> Tuple[MidiPort, ...]:
        """The inputs as they stand now, in the order the library lists them.

        Raises:
            MidiPortError: If the library fails to list them.
        """

    def open(self, port: MidiPort, sink: MidiSink) -> None:
        """Reads ``port`` from now on, handing each message to ``sink``.

        Raises:
            MidiPortError: If the library fails to open the port, or the port is gone.
        """

    def close(self) -> None:
        """Stops reading the open port, once ``sink`` hears nothing more."""
