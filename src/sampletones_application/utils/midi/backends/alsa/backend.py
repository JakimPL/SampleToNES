from typing import Final, Optional, Tuple

from sampletones_application.utils.midi.backends.protocol import MidiPort, MidiSink
from sampletones_shared.exceptions import MidiPortError

from .library import SequencerLibrary
from .reader import AlsaReader

ADDRESS_LENGTH: Final[int] = 2


class AlsaMidiBackend:
    """MIDI input through the ALSA sequencer, the way Linux delivers MIDI to every program.

    A port is a sequencer port, addressed by its client and port numbers, and named by its port name. The
    sequencer lists ports as they come and go, so a listing is always current, and a reader of its own
    client goes on reading while another lists. Each open port is read by an :class:`AlsaReader`.
    """

    def __init__(self, library: SequencerLibrary) -> None:
        self._library = library
        self._reader: Optional[AlsaReader] = None

    def describe(self) -> str:
        return self._library.describe()

    def ports(self) -> Tuple[MidiPort, ...]:
        return self._library.ports()

    def open(self, port: MidiPort, sink: MidiSink) -> None:
        self.close()
        if len(port.address) != ADDRESS_LENGTH:
            raise MidiPortError(f"The port {port.name!r} carries no sequencer address: {port.address}")

        source = (port.address[0], port.address[1])
        reader = AlsaReader(self._library.connect(source), source=source, sink=sink, library=self._library)
        reader.start()
        self._reader = reader

    def close(self) -> None:
        reader, self._reader = self._reader, None
        if reader is not None:
            reader.stop()
