import threading
import time
from typing import Final, Iterator

import pytest

from sampletones_application.utils.midi import MidiAllNotesOff, MidiInputManager, MidiNoteOn, MidiPedal
from sampletones_application.utils.midi.backends.alsa import AlsaMidiBackend, AlsaMidiLibrary
from sampletones_application.utils.midi.backends.alsa.reader import READER_NAME
from tests.suite.midi import RecordingListener

alsa_midi = pytest.importorskip("alsa_midi", reason="alsa-midi is installed on Linux alone")

KEYBOARD_CLIENT: Final[str] = "SampleToNES test keyboard"
KEYBOARD_PORT: Final[str] = "SampleToNES test keys"
SETTLE_SECONDS: Final[float] = 0.05
SETTLED_SECONDS: Final[float] = 0.1
STALE_NOTE: Final[int] = 59
PLAYED_NOTE: Final[int] = 60
VELOCITY: Final[int] = 100


class Keyboard:
    """A keyboard on the system's sequencer: a client of its own with one port the application can read."""

    def __init__(self) -> None:
        self.client = alsa_midi.SequencerClient(KEYBOARD_CLIENT)
        self._port = self.client.create_port(
            KEYBOARD_PORT,
            caps=alsa_midi.READ_PORT,
            type=alsa_midi.PortType.MIDI_GENERIC | alsa_midi.PortType.HARDWARE,
        )

    def play(self, event: object) -> None:
        self.client.event_output(event, port=self._port)
        self.client.drain_output()

    def unplug(self) -> None:
        self.client.close()


def _sequencer_or_skip() -> None:
    try:
        alsa_midi.SequencerClient(KEYBOARD_CLIENT).close()
    except alsa_midi.Error as error:
        pytest.skip(f"no ALSA sequencer on this machine: {error}")


@pytest.fixture
def keyboard() -> Iterator[Keyboard]:
    _sequencer_or_skip()
    keyboard = Keyboard()
    yield keyboard
    keyboard.unplug()


@pytest.fixture
def listener() -> RecordingListener:
    return RecordingListener()


@pytest.fixture
def manager(listener: RecordingListener) -> Iterator[MidiInputManager]:
    manager = MidiInputManager(
        AlsaMidiBackend(AlsaMidiLibrary()),
        listener=listener,
        settle_seconds=SETTLE_SECONDS,
        clock=time.monotonic,
    )
    yield manager
    manager.disconnect()


class TestTheSystemsSequencer:
    """A keyboard on the system's sequencer is listed, read, and heard leaving, through the system's ALSA."""

    def test_a_keyboard_is_listed_by_its_port_name(self, keyboard: Keyboard, manager: MidiInputManager) -> None:
        assert KEYBOARD_PORT in manager.ports()

    def test_a_keyboard_played_reaches_the_listener_after_the_port_settles(
        self,
        keyboard: Keyboard,
        manager: MidiInputManager,
        listener: RecordingListener,
    ) -> None:
        assert manager.connect(KEYBOARD_PORT)
        keyboard.play(alsa_midi.NoteOnEvent(note=STALE_NOTE, velocity=VELOCITY, channel=0))
        time.sleep(SETTLED_SECONDS)

        keyboard.play(alsa_midi.NoteOnEvent(note=PLAYED_NOTE, velocity=VELOCITY, channel=0))

        played = MidiNoteOn(note=PLAYED_NOTE, velocity=VELOCITY)
        assert listener.wait_for(played) == [played]

    def test_an_unplugged_keyboard_lets_every_key_go_and_is_told_lost(
        self,
        keyboard: Keyboard,
        manager: MidiInputManager,
        listener: RecordingListener,
    ) -> None:
        manager.connect(KEYBOARD_PORT)

        keyboard.unplug()
        listener.wait_for_loss()

        assert listener.messages == [MidiAllNotesOff(), MidiPedal(down=False)]
        assert listener.losses == [KEYBOARD_PORT]

    def test_a_disconnection_wakes_the_reader_and_ends_it(self, keyboard: Keyboard, manager: MidiInputManager) -> None:
        manager.connect(KEYBOARD_PORT)

        manager.disconnect()

        assert not [thread for thread in threading.enumerate() if thread.name == READER_NAME]
