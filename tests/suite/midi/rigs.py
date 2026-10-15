from typing import Protocol

from automation.boundaries.midi import ScriptedMidiInput
from sampletones_application.utils.midi.backends import MidiInputBackend
from sampletones_application.utils.midi.backends.alsa import AlsaMidiBackend
from sampletones_application.utils.midi.backends.portmidi import PortMidiBackend

from .portmidi import FakePortMidi
from .sequencer import FakeSequencer


class BackendRig(Protocol):
    """A backend and the system under it, which a case plugs keyboards into, plays and breaks."""

    @property
    def backend(self) -> MidiInputBackend: ...

    def offer(self, name: str) -> None:
        """Plugs in a keyboard named ``name``."""

    def play(self, name: str, message: bytes) -> None:
        """Sends ``message`` from the keyboard named ``name``."""

    def unplug(self, name: str) -> None: ...

    def fail(self) -> None:
        """Makes the library fail every call from now on."""


class AlsaRig:
    """The ALSA backend over a fake sequencer."""

    def __init__(self) -> None:
        self.sequencer = FakeSequencer()
        self._backend = AlsaMidiBackend(self.sequencer)

    @property
    def backend(self) -> AlsaMidiBackend:
        return self._backend

    def offer(self, name: str) -> None:
        self.sequencer.offer(name)

    def play(self, name: str, message: bytes) -> None:
        self.sequencer.play(name, message)

    def unplug(self, name: str) -> None:
        self.sequencer.unplug(name)

    def fail(self) -> None:
        self.sequencer.failing = True


class PortMidiRig:
    """The PortMidi backend over a fake PortMidi."""

    def __init__(self) -> None:
        self.portmidi = FakePortMidi()
        self._backend = PortMidiBackend(lambda: self.portmidi)

    @property
    def backend(self) -> PortMidiBackend:
        return self._backend

    def offer(self, name: str) -> None:
        self.portmidi.offer(name)

    def play(self, name: str, message: bytes) -> None:
        self.portmidi.play(name, message)

    def unplug(self, name: str) -> None:
        self.portmidi.unplug(name)

    def fail(self) -> None:
        self.portmidi.failing = True


class FakeRig:
    """The fake backend the manager is tested over, held to the same protocol."""

    def __init__(self) -> None:
        self._backend = ScriptedMidiInput()

    @property
    def backend(self) -> ScriptedMidiInput:
        return self._backend

    def offer(self, name: str) -> None:
        self._backend.offer(name)

    def play(self, name: str, message: bytes) -> None:
        self._backend.play(name, message)

    def unplug(self, name: str) -> None:
        self._backend.unplug(name)

    def fail(self) -> None:
        self._backend.failing = True
