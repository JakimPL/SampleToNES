import threading
from typing import Final, Iterator, List

import pytest

from sampletones_application.utils.midi.backends import MidiPort
from sampletones_application.utils.midi.backends.portmidi import PortMidiBackend
from sampletones_application.utils.midi.backends.portmidi.backend import THREAD_NAME
from sampletones_application.utils.midi.backends.portmidi.library import PortMidiLibrary
from sampletones_shared.exceptions import MidiPortError
from tests.suite.midi import FakePortMidi, RecordingSink

KEYBOARD: Final[str] = "Keyboard"
OTHER: Final[str] = "Other Keyboard"
NOTE: Final[bytes] = bytes((0x90, 60, 100))
PAST_THE_LIST: Final[int] = 99
MISSING_LIBRARY: Final[str] = "No module named 'pygame'"


class CountingLoader:
    """Loads the fake PortMidi, keeping the thread each load ran on."""

    def __init__(self, portmidi: FakePortMidi) -> None:
        self._portmidi = portmidi
        self.threads: List[str] = []

    def __call__(self) -> PortMidiLibrary:
        self.threads.append(threading.current_thread().name)
        return self._portmidi


class CallThreads(FakePortMidi):
    """A fake PortMidi keeping the thread every call into it ran on."""

    def __init__(self) -> None:
        super().__init__()
        self.threads: List[str] = []

    def Initialize(self) -> None:  # pylint: disable=invalid-name
        self.threads.append(threading.current_thread().name)
        super().Initialize()

    def CountDevices(self) -> int:  # pylint: disable=invalid-name
        self.threads.append(threading.current_thread().name)
        return super().CountDevices()


@pytest.fixture
def portmidi() -> FakePortMidi:
    portmidi = FakePortMidi()
    portmidi.offer(KEYBOARD)
    return portmidi


@pytest.fixture
def loader(portmidi: FakePortMidi) -> CountingLoader:
    return CountingLoader(portmidi)


@pytest.fixture
def backend(loader: CountingLoader) -> Iterator[PortMidiBackend]:
    backend = PortMidiBackend(loader)
    yield backend
    backend.close()


class TestTheLibrarysThread:
    """PortMidi loads once, on the backend's own thread, and every call into it runs there."""

    def test_the_library_loads_once_on_the_backends_thread(
        self,
        backend: PortMidiBackend,
        loader: CountingLoader,
    ) -> None:
        backend.ports()
        backend.ports()

        assert loader.threads == [THREAD_NAME]

    def test_every_call_into_the_library_runs_on_the_backends_thread(self) -> None:
        portmidi = CallThreads()
        portmidi.offer(KEYBOARD)
        backend = PortMidiBackend(lambda: portmidi)

        backend.open(backend.ports()[0], RecordingSink())
        backend.close()

        assert portmidi.threads
        assert set(portmidi.threads) == {THREAD_NAME}

    def test_a_library_that_fails_to_load_is_refused(self) -> None:
        def missing() -> PortMidiLibrary:
            raise ImportError(MISSING_LIBRARY)

        with pytest.raises(MidiPortError, match="failed to load"):
            PortMidiBackend(missing).ports()


class TestTheFixedList:
    """PortMidi's list stays as it was at its initialization, so a listing initializes it again."""

    def test_each_listing_initializes_the_library_again(self, backend: PortMidiBackend, portmidi: FakePortMidi) -> None:
        backend.ports()
        portmidi.offer(OTHER)

        names = [port.name for port in backend.ports()]

        assert portmidi.initializations == 2
        assert names == [KEYBOARD, OTHER]

    def test_a_listing_opens_the_port_left_open_again(
        self,
        backend: PortMidiBackend,
        portmidi: FakePortMidi,
    ) -> None:
        sink = RecordingSink()
        backend.open(backend.ports()[0], sink)
        first = portmidi.open_inputs(KEYBOARD)

        backend.ports()

        assert all(stream.closed for stream in first)
        assert len(portmidi.open_inputs(KEYBOARD)) == 1


class TestOpeningSafely:
    """An input opens only at a place the latest listing gave it under the same name."""

    def test_a_place_past_the_list_is_refused(self, backend: PortMidiBackend, portmidi: FakePortMidi) -> None:
        backend.ports()

        with pytest.raises(MidiPortError):
            backend.open(MidiPort(name=KEYBOARD, address=(PAST_THE_LIST,)), RecordingSink())

        assert not portmidi.crashed

    def test_a_place_holding_another_name_is_refused(self, backend: PortMidiBackend) -> None:
        backend.ports()

        with pytest.raises(MidiPortError):
            backend.open(MidiPort(name=OTHER, address=(0,)), RecordingSink())

    def test_an_output_is_refused(self, backend: PortMidiBackend) -> None:
        backend.ports()

        with pytest.raises(MidiPortError):
            backend.open(MidiPort(name=KEYBOARD, address=(1,)), RecordingSink())

    def test_a_port_from_no_listing_is_refused(self, backend: PortMidiBackend) -> None:
        with pytest.raises(MidiPortError):
            backend.open(MidiPort(name=KEYBOARD, address=(0,)), RecordingSink())

    def test_the_listed_place_opens(self, backend: PortMidiBackend, portmidi: FakePortMidi) -> None:
        backend.open(backend.ports()[0], RecordingSink())

        assert len(portmidi.open_inputs(KEYBOARD)) == 1


class TestAFailingInput:
    """An input failing as it is read is told lost and let go."""

    def test_an_input_failing_as_it_is_read_is_lost(self, backend: PortMidiBackend, portmidi: FakePortMidi) -> None:
        sink = RecordingSink()
        backend.open(backend.ports()[0], sink)

        portmidi.open_inputs(KEYBOARD)[0].failing = True

        sink.wait_for_loss()
        assert sink.losses == 1
