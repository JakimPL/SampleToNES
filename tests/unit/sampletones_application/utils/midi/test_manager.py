import threading
from typing import Final, Iterator

import pytest

from sampletones_application.utils.midi import (
    MidiAllNotesOff,
    MidiInputManager,
    MidiMessage,
    MidiNoteOn,
    MidiPedal,
)
from sampletones_shared.exceptions import MidiPortError
from tests.suite.application import ManualClock
from tests.suite.midi import FakeMidiBackend, RecordingListener

KEYBOARD: Final[str] = "Keyboard"
OTHER: Final[str] = "Other Keyboard"
UNKNOWN: Final[str] = "Unplugged Keyboard"
SETTLE_SECONDS: Final[float] = 0.25
CLOCK_START: Final[float] = 100.0
STALE: Final[bytes] = bytes((0x90, 59, 40))
NOTE: Final[bytes] = bytes((0x90, 60, 100))
OTHER_NOTE: Final[bytes] = bytes((0x90, 64, 90))
PITCH_BEND: Final[bytes] = bytes((0xE0, 0x00, 0x40))
RELEASE: Final = [MidiAllNotesOff(), MidiPedal(down=False)]
GATE_SECONDS: Final[float] = 5.0


@pytest.fixture
def backend() -> FakeMidiBackend:
    backend = FakeMidiBackend()
    backend.offer(KEYBOARD)
    backend.offer(OTHER)
    return backend


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(CLOCK_START)


@pytest.fixture
def listener() -> RecordingListener:
    return RecordingListener()


@pytest.fixture
def manager(backend: FakeMidiBackend, listener: RecordingListener, clock: ManualClock) -> Iterator[MidiInputManager]:
    manager = MidiInputManager(backend, listener=listener, settle_seconds=SETTLE_SECONDS, clock=clock)
    yield manager
    backend.close()


def _settled(manager: MidiInputManager, name: str, clock: ManualClock) -> None:
    assert manager.connect(name)
    clock.advance(SETTLE_SECONDS)


class TestConnecting:
    """A port is read by its name, found in a listing made at the connection."""

    def test_a_port_named_is_read(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
        clock: ManualClock,
    ) -> None:
        _settled(manager, OTHER, clock)

        backend.play(OTHER, NOTE)

        assert manager.port_name == OTHER
        assert listener.wait_for(MidiNoteOn(note=60, velocity=100)) == [MidiNoteOn(note=60, velocity=100)]

    def test_a_name_no_port_has_opens_nothing(self, manager: MidiInputManager, backend: FakeMidiBackend) -> None:
        assert not manager.connect(UNKNOWN)
        assert manager.port_name is None
        assert backend.opened == []

    def test_a_port_plugged_in_after_the_start_is_found(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
    ) -> None:
        backend.offer(UNKNOWN)

        assert manager.connect(UNKNOWN)
        assert backend.opened == [UNKNOWN]

    def test_the_ports_are_named_as_they_stand(self, manager: MidiInputManager, backend: FakeMidiBackend) -> None:
        backend.unplug(OTHER)

        assert manager.ports() == (KEYBOARD,)


class TestSettling:
    """What a port sends as it opens is a device's backlog, so it stays silent, and what follows plays."""

    def test_messages_arriving_as_the_port_opens_are_dropped(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
        clock: ManualClock,
    ) -> None:
        manager.connect(KEYBOARD)
        backend.play(KEYBOARD, STALE)
        backend.drain()

        clock.advance(SETTLE_SECONDS)
        backend.play(KEYBOARD, NOTE)

        assert listener.wait_for(MidiNoteOn(note=60, velocity=100)) == [MidiNoteOn(note=60, velocity=100)]

    def test_messages_that_play_nothing_reach_nobody(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
        clock: ManualClock,
    ) -> None:
        _settled(manager, KEYBOARD, clock)

        backend.play(KEYBOARD, PITCH_BEND)
        backend.play(KEYBOARD, NOTE)

        assert listener.wait_for(MidiNoteOn(note=60, velocity=100)) == [MidiNoteOn(note=60, velocity=100)]


class TestLettingKeysGo:
    """Whenever the keys stop reaching the listener, it hears every key let go and the pedal come up."""

    def test_disconnecting_lets_every_key_go(self, manager: MidiInputManager, listener: RecordingListener) -> None:
        manager.connect(KEYBOARD)

        manager.disconnect()

        assert listener.messages == RELEASE
        assert manager.port_name is None

    def test_disconnecting_with_no_port_read_tells_nothing(
        self,
        manager: MidiInputManager,
        listener: RecordingListener,
    ) -> None:
        manager.disconnect()

        assert listener.messages == []

    def test_changing_ports_lets_the_keys_of_the_port_before_go(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
        clock: ManualClock,
    ) -> None:
        _settled(manager, KEYBOARD, clock)

        _settled(manager, OTHER, clock)
        backend.play(KEYBOARD, NOTE)
        backend.play(OTHER, OTHER_NOTE)

        assert listener.wait_for(MidiNoteOn(note=64, velocity=90)) == [*RELEASE, MidiNoteOn(note=64, velocity=90)]

    def test_an_unplugged_port_lets_every_key_go_and_is_told_lost(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
    ) -> None:
        manager.connect(KEYBOARD)

        backend.unplug(KEYBOARD)
        listener.wait_for_loss()

        assert listener.messages == RELEASE
        assert listener.losses == [KEYBOARD]
        assert manager.port_name is None

    def test_disconnecting_after_a_loss_tells_nothing_more(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
    ) -> None:
        manager.connect(KEYBOARD)
        backend.unplug(KEYBOARD)
        listener.wait_for_loss()

        manager.disconnect()

        assert listener.messages == RELEASE


class GatedListener(RecordingListener):
    """A listener holding the backend's thread in its first message until the case opens the gate."""

    def __init__(self) -> None:
        super().__init__()
        self.inside = threading.Event()
        self.gate = threading.Event()

    def heard(self, message: MidiMessage) -> None:
        if not self.inside.is_set():
            self.inside.set()
            assert self.gate.wait(timeout=GATE_SECONDS)

        super().heard(message)


class TestALossRacingASwitch:
    """A port lost while the reader switches ports is a port the reader let go, so nobody hears it lost."""

    def test_a_loss_arriving_during_a_switch_tells_nothing(
        self,
        backend: FakeMidiBackend,
        clock: ManualClock,
    ) -> None:
        listener = GatedListener()
        manager = MidiInputManager(backend, listener=listener, settle_seconds=SETTLE_SECONDS, clock=clock)
        _settled(manager, KEYBOARD, clock)
        backend.play(KEYBOARD, NOTE)
        assert listener.inside.wait(timeout=GATE_SECONDS)
        backend.unplug(KEYBOARD)

        switching = threading.Thread(target=manager.connect, args=(OTHER,))
        switching.start()
        while manager.port_name == KEYBOARD:
            switching.join(timeout=0.001)

        listener.gate.set()
        switching.join(timeout=GATE_SECONDS)
        backend.close()

        assert listener.losses == []
        assert listener.messages == [MidiNoteOn(note=60, velocity=100), *RELEASE]


class TestRefreshing:
    """A refresh lists the inputs again and reads the port read before by its name."""

    def test_a_refresh_reads_the_port_read_before_again(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
        listener: RecordingListener,
        clock: ManualClock,
    ) -> None:
        _settled(manager, KEYBOARD, clock)

        names = manager.refresh()
        clock.advance(SETTLE_SECONDS)
        backend.play(KEYBOARD, NOTE)

        assert names == (KEYBOARD, OTHER)
        assert backend.opened == [KEYBOARD, KEYBOARD]
        assert listener.wait_for(MidiNoteOn(note=60, velocity=100)) == [*RELEASE, MidiNoteOn(note=60, velocity=100)]

    def test_a_refresh_with_no_port_read_opens_nothing(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
    ) -> None:
        backend.offer(UNKNOWN)

        assert manager.refresh() == (KEYBOARD, OTHER, UNKNOWN)
        assert backend.opened == []
        assert manager.port_name is None


class TestFailures:
    """A library failing leaves nothing read and raises to the caller."""

    def test_a_failing_listing_raises_and_reads_nothing(
        self,
        manager: MidiInputManager,
        backend: FakeMidiBackend,
    ) -> None:
        manager.connect(KEYBOARD)
        backend.failing = True

        with pytest.raises(MidiPortError):
            manager.connect(OTHER)

        assert manager.port_name is None
