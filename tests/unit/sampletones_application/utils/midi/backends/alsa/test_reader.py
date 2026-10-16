from typing import Final, Iterator

import pytest

from sampletones_application.utils.midi.backends import MidiPort
from sampletones_application.utils.midi.backends.alsa import AlsaMidiBackend
from sampletones_application.utils.midi.backends.alsa import reader as reader_module
from sampletones_application.utils.midi.backends.alsa.library import SequencerCut, SequencerLeft
from tests.suite.midi import ClosingSink, FakeSequencer, RecordingSink

KEYBOARD: Final[str] = "Keyboard"
NOTE: Final[bytes] = bytes((0x90, 60, 100))
OTHER_CLIENT: Final[int] = 64
OTHER_PORT: Final[int] = 7
SHORT_JOIN_SECONDS: Final[float] = 0.05


@pytest.fixture
def sequencer() -> FakeSequencer:
    sequencer = FakeSequencer()
    sequencer.offer(KEYBOARD)
    return sequencer


@pytest.fixture
def backend(sequencer: FakeSequencer) -> Iterator[AlsaMidiBackend]:
    backend = AlsaMidiBackend(sequencer)
    yield backend
    sequencer.failing = False
    backend.close()


@pytest.fixture
def sink() -> RecordingSink:
    return RecordingSink()


def _opened(backend: AlsaMidiBackend, sink: RecordingSink) -> MidiPort:
    port = backend.ports()[0]
    backend.open(port, sink)
    return port


class TestWhatTakesTheSourceAway:
    """The source is gone once its client or its own port leaves, or its subscription is cut, and not otherwise."""

    def test_the_sources_port_leaving_is_a_loss(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        port = _opened(backend, sink)

        sequencer.announce(SequencerLeft(client=port.address[0], port=port.address[1]))

        sink.wait_for_loss()

    def test_another_port_of_the_sources_client_leaving_changes_nothing(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        port = _opened(backend, sink)

        sequencer.announce(SequencerLeft(client=port.address[0], port=OTHER_PORT))
        sequencer.play(KEYBOARD, NOTE)

        assert sink.wait_for_messages(1) == [NOTE]
        assert sink.losses == 0

    def test_another_client_leaving_changes_nothing(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        _opened(backend, sink)

        sequencer.announce(SequencerLeft(client=OTHER_CLIENT, port=None))
        sequencer.play(KEYBOARD, NOTE)

        assert sink.wait_for_messages(1) == [NOTE]
        assert sink.losses == 0

    def test_the_readers_subscription_cut_is_a_loss(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        port = _opened(backend, sink)
        reader = sequencer.connections[0]

        sequencer.announce(SequencerCut(sender=(port.address[0], port.address[1]), destination=reader.address))

        sink.wait_for_loss()

    def test_a_subscription_cut_elsewhere_changes_nothing(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        port = _opened(backend, sink)

        sequencer.announce(SequencerCut(sender=(port.address[0], port.address[1]), destination=(OTHER_CLIENT, 0)))
        sequencer.play(KEYBOARD, NOTE)

        assert sink.wait_for_messages(1) == [NOTE]
        assert sink.losses == 0

    def test_a_sequencer_failing_to_deliver_is_a_loss(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        _opened(backend, sink)

        sequencer.break_delivery()

        sink.wait_for_loss()


class TestStopping:
    """A stop wakes the reader and lets its connection go, from the caller's thread or the sink's own call."""

    def test_a_close_wakes_the_reader_and_lets_its_connection_go(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
    ) -> None:
        _opened(backend, sink)
        connection = sequencer.connections[0]

        backend.close()

        assert sequencer.wakes == 1
        assert connection.closed

    def test_a_close_from_the_sinks_own_call_ends_the_reader(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
    ) -> None:
        closing = ClosingSink(backend)
        backend.open(backend.ports()[0], closing)
        connection = sequencer.connections[0]

        sequencer.play(KEYBOARD, NOTE)
        closing.wait_for_messages(1)

        assert connection.closed
        assert sequencer.wakes == 0

    def test_a_reader_the_sequencer_fails_to_wake_is_left_with_its_connection(
        self,
        backend: AlsaMidiBackend,
        sequencer: FakeSequencer,
        sink: RecordingSink,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(reader_module, "JOIN_SECONDS", SHORT_JOIN_SECONDS)
        _opened(backend, sink)
        connection = sequencer.connections[0]
        sequencer.failing = True

        backend.close()

        assert not connection.closed
        connection.deliver(None)
