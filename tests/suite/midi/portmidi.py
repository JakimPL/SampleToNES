import threading
from dataclasses import dataclass
from typing import Final, List, Optional, Sequence, Tuple

from sampletones_application.utils.midi.backends.portmidi.library import DeviceInfo, PackedEvent

INTERFACE: Final[bytes] = b"Fake"
PACKED_LENGTH: Final[int] = 4
PORTMIDI_FAILURE: Final[str] = "PortMidi: Host error"
CRASH: Final[str] = "PortMidi opened a place past its list, which ends the process"


@dataclass(frozen=True)
class FakeDevice:
    name: str
    is_input: bool


class FakeInput:
    """An open PortMidi input: events wait until a poll finds them, and a failing input raises on its next poll."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = threading.Lock()
        self._events: List[PackedEvent] = []
        self.failing: bool = False
        self.closed: bool = False

    def Poll(self) -> int:  # pylint: disable=invalid-name
        with self._lock:
            if self.failing:
                raise Exception(PORTMIDI_FAILURE)  # pylint: disable=broad-exception-raised

            return int(bool(self._events))

    def Read(self, max_events: int) -> Sequence[PackedEvent]:  # pylint: disable=invalid-name
        with self._lock:
            events, self._events = self._events[:max_events], self._events[max_events:]
            return events

    def Close(self) -> None:  # pylint: disable=invalid-name
        self.closed = True

    def push(self, message: bytes) -> None:
        packed = list(message[:PACKED_LENGTH]) + [0] * (PACKED_LENGTH - len(message[:PACKED_LENGTH]))
        with self._lock:
            self._events.append((packed, 0))


class FakePortMidi:
    """PortMidi as ``pygame.pypm`` offers it, with the quirks the backend works around.

    The device list stays as it stood at the latest initialization, inputs and outputs share it, names come as
    bytes, every failure is a bare ``Exception``, and opening a place past the list marks the fake crashed, since
    the real library ends the process there.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.devices: List[FakeDevice] = []
        self._listed: List[FakeDevice] = []
        self.initialized: bool = False
        self.initializations: int = 0
        self.failing: bool = False
        self.crashed: bool = False
        self.inputs: List[FakeInput] = []

    def Initialize(self) -> None:  # pylint: disable=invalid-name
        self._check()
        with self._lock:
            self._listed = list(self.devices)
            self.initialized = True
            self.initializations += 1

    def Terminate(self) -> None:  # pylint: disable=invalid-name
        with self._lock:
            self.initialized = False

    def CountDevices(self) -> int:  # pylint: disable=invalid-name
        self._check()
        with self._lock:
            return len(self._listed)

    def GetDeviceInfo(self, device_id: int) -> Optional[DeviceInfo]:  # pylint: disable=invalid-name
        with self._lock:
            if not 0 <= device_id < len(self._listed):
                return None

            device = self._listed[device_id]

        return (INTERFACE, device.name.encode(), int(device.is_input), int(not device.is_input), 0)

    def Input(self, device_id: int, buffer_size: int) -> FakeInput:  # pylint: disable=invalid-name
        del buffer_size
        self._check()
        with self._lock:
            if not 0 <= device_id < len(self._listed):
                self.crashed = True
                raise Exception(CRASH)  # pylint: disable=broad-exception-raised

            device = self._listed[device_id]
            if not device.is_input or device not in self.devices:
                raise Exception(PORTMIDI_FAILURE)  # pylint: disable=broad-exception-raised

            stream = FakeInput(device.name)
            self.inputs.append(stream)
            return stream

    def offer(self, name: str) -> None:
        """Plugs in a keyboard, listed as an input and an output of the same name, as PortMidi lists one."""
        with self._lock:
            self.devices.extend((FakeDevice(name=name, is_input=True), FakeDevice(name=name, is_input=False)))

    def unplug(self, name: str) -> None:
        with self._lock:
            self.devices = [device for device in self.devices if device.name != name]

    def open_inputs(self, name: str) -> Tuple[FakeInput, ...]:
        with self._lock:
            return tuple(stream for stream in self.inputs if stream.name == name and not stream.closed)

    def play(self, name: str, message: bytes) -> None:
        for stream in self.open_inputs(name):
            stream.push(message)

    def _check(self) -> None:
        if self.failing:
            raise Exception(PORTMIDI_FAILURE)  # pylint: disable=broad-exception-raised
