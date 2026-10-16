import threading
from typing import Final, Optional

from sampletones_application.utils.midi.backends.protocol import MidiSink
from sampletones_shared.exceptions import MidiPortError
from sampletones_shared.logger import logger

from .library import Address, SequencerBytes, SequencerConnection, SequencerCut, SequencerLeft, SequencerLibrary

READER_NAME: Final[str] = "MidiReader"
SYSTEM_EXCLUSIVE: Final[int] = 0xF0
JOIN_SECONDS: Final[float] = 2.0


class AlsaReader:
    """One source read on a thread of its own, from its connection to the sequencer until it stops.

    The thread waits in the sequencer for each event and hands every message to the sink, system exclusive
    messages aside. The source counts as gone once it leaves the sequencer, as an unplugged keyboard does, or
    once its subscription is cut: the sink hears it once and the thread ends. A stop is a flag the thread
    reads as it wakes, and a wake sent to the input port is what wakes it.
    """

    def __init__(
        self,
        connection: SequencerConnection,
        *,
        source: Address,
        sink: MidiSink,
        library: SequencerLibrary,
    ) -> None:
        """Holds the connection and who hears it.

        Args:
            connection: The client whose input port reads ``source``, read here alone.
            source: The port the messages come from.
            sink: What hears the messages, and the source going away.
            library: The sequencer, which wakes the thread for a stop.
        """
        self._connection = connection
        self._source = source
        self._sink = sink
        self._library = library
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run, name=READER_NAME, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        """Stops the thread and closes the connection, once the sink hears nothing more.

        A stop from the sink's own call lets the thread end as that call returns.
        """
        self._stopping.set()
        if threading.current_thread() is not self._thread:
            self._wake()
            self._thread.join(timeout=JOIN_SECONDS)
            if self._thread.is_alive():
                logger.error(f"AlsaReader: {READER_NAME} outlived its stop")
                return

        self._connection.close()

    def _wake(self) -> None:
        """Wakes the thread waiting in the sequencer; one failing to answer leaves the join to its deadline."""
        try:
            self._library.wake(self._connection.address)
        except MidiPortError as error:
            logger.error_with_traceback(error, "The ALSA sequencer failed to wake the reader")

    def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                event = self._connection.next_event()
            except MidiPortError as error:
                logger.error_with_traceback(error, "The ALSA sequencer stopped delivering")
                self._lose()
                return

            if self._stopping.is_set():
                return

            match event:
                case SequencerBytes(data=data) if data and data[0] != SYSTEM_EXCLUSIVE:
                    self._sink.received(data)
                case SequencerLeft(client=client, port=port) if self._names_source(client, port):
                    self._lose()
                    return
                case SequencerCut(sender=sender, destination=destination) if (
                    sender == self._source and destination == self._connection.address
                ):
                    self._lose()
                    return

    def _names_source(self, client: int, port: Optional[int]) -> bool:
        """Whether a client or port leaving takes the source with it."""
        source_client, source_port = self._source
        return client == source_client and port in (None, source_port)

    def _lose(self) -> None:
        if not self._stopping.is_set():
            self._sink.lost()
