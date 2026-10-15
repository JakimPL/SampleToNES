from sampletones_application.utils.midi.backends import MidiInputBackend
from sampletones_application.utils.midi.backends.alsa import AlsaMidiBackend, AlsaMidiLibrary
from sampletones_application.utils.midi.backends.portmidi import PortMidiBackend, load_portmidi
from sampletones_shared.utils.system.system import System


def select_midi_backend() -> MidiInputBackend:
    """The MIDI backend that reaches the running system's own MIDI service.

    Linux delivers MIDI through the ALSA sequencer, read with the system's own ALSA library, which finds the
    sequencer through the system's configuration. Windows and macOS are read through PortMidi. Neither library
    loads until a port is listed, so choosing a backend costs nothing at startup.
    """
    match System.current():
        case System.LINUX:
            return AlsaMidiBackend(AlsaMidiLibrary())
        case System.WINDOWS | System.MACOS:
            return PortMidiBackend(load_portmidi)
