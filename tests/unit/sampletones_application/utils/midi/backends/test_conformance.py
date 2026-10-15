import threading
from typing import Callable, Dict, Final, Iterator

import pytest

from sampletones_application.utils.midi.backends import MidiPort
from sampletones_shared.exceptions import MidiPortError
from tests.suite.midi import AlsaRig, BackendRig, ClosingSink, FakeRig, PortMidiRig, RecordingSink

KEYBOARD: Final[str] = "Keyboard"
OTHER: Final[str] = "Other Keyboard"
NOTE_ON: Final[bytes] = bytes((0x90, 60, 100))
OTHER_NOTE: Final[bytes] = bytes((0x90, 64, 90))
NOTE_OFF: Final[bytes] = bytes((0x80, 60, 0))
SYSTEM_EXCLUSIVE: Final[bytes] = bytes((0xF0, 0x7E, 0x7F, 0xF7))

RIGS: Final[Dict[str, Callable[[], BackendRig]]] = {
    "alsa": AlsaRig,
    "portmidi": PortMidiRig,
    "fake": FakeRig,
}


@pytest.fixture(params=list(RIGS), ids=list(RIGS))
def rig(request: pytest.FixtureRequest) -> Iterator[BackendRig]:
    """Each backend over the system a case drives, offering one keyboard and let go once the case ends."""
    backend_rig = RIGS[request.param]()
    backend_rig.offer(KEYBOARD)
    yield backend_rig
    backend_rig.backend.close()


@pytest.fixture
def sink() -> RecordingSink:
    return RecordingSink()


def _port(rig: BackendRig, name: str) -> MidiPort:
    return next(port for port in rig.backend.ports() if port.name == name)


def _opened(rig: BackendRig, name: str, sink: RecordingSink) -> RecordingSink:
    rig.backend.open(_port(rig, name), sink)
    return sink


class TestListing:
    """A listing names every input as it stands now, and leaves an open port delivering."""

    def test_every_keyboard_plugged_in_is_listed_once(self, rig: BackendRig) -> None:
        rig.offer(OTHER)

        names = [port.name for port in rig.backend.ports()]

        assert sorted(names) == sorted((KEYBOARD, OTHER))

    def test_a_keyboard_unplugged_is_left_out_of_the_next_listing(self, rig: BackendRig) -> None:
        rig.offer(OTHER)

        rig.unplug(OTHER)

        assert [port.name for port in rig.backend.ports()] == [KEYBOARD]

    def test_listing_leaves_the_open_port_delivering(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)

        rig.backend.ports()
        rig.play(KEYBOARD, NOTE_ON)

        assert sink.wait_for_messages(1) == [NOTE_ON]


class TestReading:
    """An open port hands over each complete message in order, from a thread of the backend's own."""

    def test_an_open_port_hands_over_every_message_in_order(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)

        for message in (NOTE_ON, OTHER_NOTE, NOTE_OFF):
            rig.play(KEYBOARD, message)

        assert sink.wait_for_messages(3) == [NOTE_ON, OTHER_NOTE, NOTE_OFF]

    def test_a_port_left_closed_stays_silent(self, rig: BackendRig, sink: RecordingSink) -> None:
        rig.offer(OTHER)
        _opened(rig, KEYBOARD, sink)

        rig.play(OTHER, OTHER_NOTE)
        rig.play(KEYBOARD, NOTE_ON)

        assert sink.wait_for_messages(1) == [NOTE_ON]

    def test_system_exclusive_stays_behind(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)

        rig.play(KEYBOARD, SYSTEM_EXCLUSIVE)
        rig.play(KEYBOARD, NOTE_ON)

        assert sink.wait_for_messages(1) == [NOTE_ON]

    def test_the_sink_hears_from_a_thread_of_the_backend(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)

        rig.play(KEYBOARD, NOTE_ON)
        sink.wait_for_messages(1)

        assert threading.current_thread().name not in sink.threads


class TestOpeningAndClosing:
    """One port is read at a time, and a closed port reaches its sink no more."""

    def test_opening_another_port_closes_the_one_before(self, rig: BackendRig, sink: RecordingSink) -> None:
        rig.offer(OTHER)
        _opened(rig, KEYBOARD, sink)
        other = _opened(rig, OTHER, RecordingSink())

        rig.play(KEYBOARD, NOTE_ON)
        rig.play(OTHER, OTHER_NOTE)

        assert other.wait_for_messages(1) == [OTHER_NOTE]
        assert sink.messages == []

    def test_a_closed_port_reaches_its_sink_no_more(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)
        rig.backend.close()
        rig.play(KEYBOARD, NOTE_ON)

        reopened = _opened(rig, KEYBOARD, RecordingSink())
        rig.play(KEYBOARD, OTHER_NOTE)

        assert reopened.wait_for_messages(1) == [OTHER_NOTE]
        assert sink.messages == []

    def test_a_sink_lets_its_backend_go_from_its_own_call(self, rig: BackendRig) -> None:
        closing = ClosingSink(rig.backend)
        rig.backend.open(_port(rig, KEYBOARD), closing)

        rig.play(KEYBOARD, NOTE_ON)
        closing.wait_for_messages(1)
        rig.play(KEYBOARD, OTHER_NOTE)
        reopened = _opened(rig, KEYBOARD, RecordingSink())
        rig.play(KEYBOARD, NOTE_OFF)

        assert reopened.wait_for_messages(1) == [NOTE_OFF]
        assert closing.messages == [NOTE_ON]

    def test_closing_with_no_port_open_does_nothing(self, rig: BackendRig) -> None:
        rig.backend.close()

        assert [port.name for port in rig.backend.ports()] == [KEYBOARD]

    def test_a_port_gone_since_its_listing_is_refused(self, rig: BackendRig, sink: RecordingSink) -> None:
        port = _port(rig, KEYBOARD)
        rig.unplug(KEYBOARD)

        with pytest.raises(MidiPortError):
            rig.backend.open(port, sink)


class TestLoss:
    """A keyboard going away is told once, by the next listing at the latest, and nothing more arrives from it."""

    def test_an_unplugged_keyboard_is_told_once(self, rig: BackendRig, sink: RecordingSink) -> None:
        _opened(rig, KEYBOARD, sink)

        rig.unplug(KEYBOARD)
        rig.backend.ports()
        sink.wait_for_loss()
        rig.backend.ports()

        assert sink.losses == 1

    def test_a_keyboard_plugged_back_in_reaches_the_lost_sink_no_more(
        self,
        rig: BackendRig,
        sink: RecordingSink,
    ) -> None:
        _opened(rig, KEYBOARD, sink)
        rig.unplug(KEYBOARD)
        rig.backend.ports()
        sink.wait_for_loss()

        rig.offer(KEYBOARD)
        reopened = _opened(rig, KEYBOARD, RecordingSink())
        rig.play(KEYBOARD, NOTE_ON)

        assert reopened.wait_for_messages(1) == [NOTE_ON]
        assert sink.messages == []


class TestFailures:
    """A library failing arrives as ``MidiPortError``."""

    def test_a_failing_library_refuses_a_listing(self, rig: BackendRig) -> None:
        rig.fail()

        with pytest.raises(MidiPortError):
            rig.backend.ports()

    def test_a_failing_library_refuses_an_opening(self, rig: BackendRig, sink: RecordingSink) -> None:
        port = _port(rig, KEYBOARD)
        rig.fail()

        with pytest.raises(MidiPortError):
            rig.backend.open(port, sink)
