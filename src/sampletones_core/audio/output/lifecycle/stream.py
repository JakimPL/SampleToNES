from dataclasses import dataclass
from enum import Enum


class StreamPhase(Enum):
    """The device stream's state as the thread writing to it last left it.

    A stream is closed until a playback wants it, open while the device takes what is written, and broken
    once a write failed, after which the one thing left to do with it is to let it go.
    """

    CLOSED = "closed"
    OPEN = "open"
    BROKEN = "broken"


class StreamAction(Enum):
    """What the thread writing to the device does next.

    Attributes:
        OPEN: Opens the stream on the device in force.
        WRITE: Writes one block, mixed from the playbacks sounding.
        DRAIN: Plays out what the device still holds, then closes the stream.
        ABORT: Closes the stream, cutting what the device still holds.
        RECONFIGURE: Takes the device, rate and buffer size the reader chose.
        WAIT: Sleeps until a request arrives, the stream held open while every playback present is paused.
        EXIT: Ends the thread, since nothing is left to play or the output closed for good.
    """

    OPEN = "open"
    WRITE = "write"
    DRAIN = "drain"
    ABORT = "abort"
    RECONFIGURE = "reconfigure"
    WAIT = "wait"
    EXIT = "exit"


@dataclass(frozen=True)
class StreamState:
    """A picture of the stream's lifecycle, equal for two lifecycles that answer every later event alike."""

    phase: StreamPhase
    closing: bool
    reconfiguring: bool
    cutting: bool


class StreamLifecycle:
    """The one device stream's state, which decides what the thread writing to it does next.

    The thread writing to the device is the only one to open, write, drain or close the stream, so the
    stream opens only from closed, and the device holds one stream at most. Every claim that takes the
    output plays on a stream of its own: a claim made while a stream is open cuts it, and the next stream
    opens for the new sound. Two requests reach it from the render thread and outrank playing: a
    reconfiguration lets the stream go and takes new settings before the next one opens, and a close lets
    it go for good. A sound that finished as the last one playing plays its tail out, and any other end
    cuts it. Once nothing is left to play, the writer ends, and the next claim starts another.

    The owner serializes the events, which is what lets a case check every order they can come in.
    """

    def __init__(self) -> None:
        self._phase = StreamPhase.CLOSED
        self._closing: bool = False
        self._reconfiguring: bool = False
        self._cutting: bool = False

    @property
    def phase(self) -> StreamPhase:
        return self._phase

    @property
    def state(self) -> StreamState:
        return StreamState(
            phase=self._phase,
            closing=self._closing,
            reconfiguring=self._reconfiguring,
            cutting=self._cutting,
        )

    @property
    def closing(self) -> bool:
        """Whether the output is closing for good, which every later claim is declined for."""
        return self._closing

    @property
    def reconfiguring(self) -> bool:
        return self._reconfiguring

    @property
    def cutting(self) -> bool:
        """Whether a claim took the output from the sound the open stream plays, which cuts that stream."""
        return self._cutting

    def next_action(self, *, wanted: bool, mixing: bool, tail: bool) -> StreamAction:
        """What the writer does next.

        Args:
            wanted: Whether a playback holds the output.
            mixing: Whether a playback holding the output sounds, which one held paused leaves silent.
            tail: Whether a sound that finished waits for its tail to play out.
        """
        if self._phase is StreamPhase.BROKEN:
            return StreamAction.ABORT

        if self._closing:
            return StreamAction.ABORT if self._phase is StreamPhase.OPEN else StreamAction.EXIT

        if self._reconfiguring:
            return StreamAction.ABORT if self._phase is StreamPhase.OPEN else StreamAction.RECONFIGURE

        if self._cutting:
            return StreamAction.ABORT

        if wanted:
            if self._phase is StreamPhase.CLOSED:
                return StreamAction.OPEN

            return StreamAction.WRITE if mixing else StreamAction.WAIT

        if self._phase is StreamPhase.OPEN:
            return StreamAction.DRAIN if tail else StreamAction.ABORT

        return StreamAction.EXIT

    def opened(self) -> None:
        if self._phase is StreamPhase.CLOSED:
            self._phase = StreamPhase.OPEN

    def write_failed(self) -> None:
        if self._phase is StreamPhase.OPEN:
            self._phase = StreamPhase.BROKEN

    def closed(self) -> None:
        self._phase = StreamPhase.CLOSED
        self._cutting = False

    def claimed(self) -> None:
        """A claim took the output, which cuts a stream already open so the new sound starts on its own."""
        if self._phase is StreamPhase.OPEN:
            self._cutting = True

    def request_reconfigure(self) -> bool:
        """Asks for new settings before the next stream opens; answers whether the output takes them."""
        if self._closing:
            return False

        self._reconfiguring = True
        return True

    def reconfigured(self) -> None:
        self._reconfiguring = False

    def request_close(self) -> None:
        self._closing = True
        self._reconfiguring = False
