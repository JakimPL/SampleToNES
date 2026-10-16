import threading
import time
from typing import Any, Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.coordinators.midi import STARTUP_THREAD_NAME, MidiCoordinator
from sampletones_application.paths import LANG_EN
from sampletones_application.utils.midi import MidiNoteOn, MidiRouter
from sampletones_application.view_model.shared.midi_settings import MidiSettingsViewModel
from sampletones_shared.types.callback import VoidCallback
from tests.suite.application import synchronous_queue
from tests.suite.midi import ScriptedMidiInput

__all__ = ["synchronous_queue"]

KEYBOARD: Final[str] = "Keyboard"
OTHER: Final[str] = "Other Keyboard"
UNPLUGGED: Final[str] = "Unplugged Keyboard"
SETTLE_SECONDS: Final[float] = 0.0
WAIT_SECONDS: Final[float] = 5.0
MIDDLE_C: Final[int] = 60
VELOCITY: Final[int] = 100


class WindowRecorder:
    """Stands in for the MIDI settings dialog, keeping what it was asked to show."""

    def __init__(self) -> None:
        self.view_models: List[MidiSettingsViewModel] = []
        self.keys: List[Tuple[str, int]] = []
        self.is_open = False
        self.on_port_changed: Any = None
        self.on_refresh: Any = None
        self.on_commit: Any = None
        self.on_cancel: Any = None

    def open(self, view_model: MidiSettingsViewModel) -> None:
        self.is_open = True
        self.view_models.append(view_model)

    def update_view(self, view_model: MidiSettingsViewModel) -> None:
        self.view_models.append(view_model)

    def hide(self) -> None:
        self.is_open = False

    def show_key(self, name: str, velocity: int) -> None:
        self.keys.append((name, velocity))

    @property
    def shown(self) -> MidiSettingsViewModel:
        return self.view_models[-1]


class SessionRecorder:
    def __init__(self, port: Optional[str]) -> None:
        self.midi_port = port
        self.velocity_sets_volume = True

    def set_midi_settings(self, port: Optional[str], *, velocity_sets_volume: bool) -> None:
        self.midi_port = port
        self.velocity_sets_volume = velocity_sets_volume


class Harness:
    """The coordinator over a fake backend and recorders, with the gestures a reader makes spelled as methods."""

    def __init__(self, backend: ScriptedMidiInput, *, saved: Optional[str]) -> None:
        self.backend = backend
        self.window = WindowRecorder()
        self.session = SessionRecorder(saved)
        self.statuses: List[str] = []
        self.posted: List[VoidCallback] = []
        self.router = MidiRouter()
        self.coordinator = MidiCoordinator(
            backend,
            self.router,
            self.session,
            window=self.window,
            language_manager=LanguageManager(LANG_EN),
            show_status=self.statuses.append,
            settle_seconds=SETTLE_SECONDS,
            clock=time.monotonic,
            post=self.posted.append,
        )

    def start(self) -> None:
        self.coordinator.start()
        self.wait_for_startup()

    def wait_for_startup(self) -> None:
        deadline = time.monotonic() + WAIT_SECONDS
        while any(thread.name == STARTUP_THREAD_NAME for thread in threading.enumerate()):
            assert time.monotonic() < deadline, "the startup never ended"
            time.sleep(0.001)

    def run_posted(self) -> None:
        posted, self.posted = self.posted, []
        for delivery in posted:
            delivery()

    def pick(self, port: Optional[str]) -> None:
        self.window.on_port_changed(port)


@pytest.fixture
def backend() -> ScriptedMidiInput:
    backend = ScriptedMidiInput()
    backend.offer(KEYBOARD)
    backend.offer(OTHER)
    return backend


@pytest.fixture
def harness(backend: ScriptedMidiInput) -> Harness:
    return Harness(backend, saved=KEYBOARD)


class TestStartup:
    """The library loads off the render thread, and the keyboard the session kept is read by its name."""

    def test_the_kept_keyboard_is_read(self, harness: Harness, backend: ScriptedMidiInput) -> None:
        harness.start()

        assert backend.opened == [KEYBOARD]

    def test_a_kept_keyboard_absent_this_run_is_left_unread(self, backend: ScriptedMidiInput) -> None:
        harness = Harness(backend, saved=UNPLUGGED)

        harness.start()

        assert backend.opened == []
        assert harness.statuses == []

    def test_with_no_keyboard_kept_nothing_is_opened(self, backend: ScriptedMidiInput) -> None:
        harness = Harness(backend, saved=None)

        harness.start()

        assert backend.opened == []

    def test_a_port_picked_during_startup_outlives_the_kept_one(self) -> None:
        backend = GatedBackend()
        backend.offer(KEYBOARD)
        backend.offer(OTHER)
        harness = Harness(backend, saved=KEYBOARD)
        harness.coordinator.start()
        assert backend.describing.wait(timeout=WAIT_SECONDS)

        picking = threading.Thread(target=harness.pick, args=(OTHER,))
        picking.start()
        backend.loaded.set()
        picking.join(timeout=WAIT_SECONDS)
        harness.wait_for_startup()

        assert backend.opened == [OTHER]


class GatedBackend(ScriptedMidiInput):
    """A backend whose library takes until the case lets it load."""

    def __init__(self) -> None:
        super().__init__()
        self.describing = threading.Event()
        self.loaded = threading.Event()

    def describe(self) -> str:
        if not self.describing.is_set():
            self.describing.set()
            assert self.loaded.wait(timeout=WAIT_SECONDS)

        return super().describe()


class TestTheDialog:
    """The dialog lists the inputs, reads a picked port at once, and OK or Cancel settles what is kept."""

    def test_the_dialog_lists_the_inputs_and_the_one_read(self, harness: Harness) -> None:
        harness.start()

        harness.coordinator.open()

        assert harness.window.shown.ports == (KEYBOARD, OTHER)
        assert harness.window.shown.port == KEYBOARD
        assert harness.window.shown.available

    def test_a_port_picked_is_read_at_once(self, harness: Harness, backend: ScriptedMidiInput) -> None:
        harness.start()
        harness.coordinator.open()

        harness.pick(OTHER)

        assert backend.opened == [KEYBOARD, OTHER]
        assert harness.window.shown.port == OTHER

    def test_a_port_gone_since_the_listing_says_why(self, harness: Harness, backend: ScriptedMidiInput) -> None:
        harness.start()
        harness.coordinator.open()
        backend.unplug(OTHER)

        harness.pick(OTHER)

        refusal = harness.window.shown.refusal
        assert refusal is not None and OTHER in refusal
        assert harness.window.shown.port is None

    def test_cancel_reads_again_the_port_the_dialog_opened_with(
        self,
        harness: Harness,
        backend: ScriptedMidiInput,
    ) -> None:
        harness.start()
        harness.coordinator.open()
        harness.pick(OTHER)

        harness.window.on_cancel()

        assert backend.opened == [KEYBOARD, OTHER, KEYBOARD]
        assert harness.session.midi_port == KEYBOARD
        assert not harness.window.is_open

    def test_cancel_with_no_change_opens_nothing_again(self, harness: Harness, backend: ScriptedMidiInput) -> None:
        harness.start()
        harness.coordinator.open()

        harness.window.on_cancel()

        assert backend.opened == [KEYBOARD]

    def test_ok_keeps_the_port_and_the_velocity_setting(self, harness: Harness) -> None:
        harness.start()
        harness.coordinator.open()
        harness.pick(None)

        harness.window.on_commit(False)

        assert harness.session.midi_port is None
        assert not harness.session.velocity_sets_volume
        assert not harness.window.is_open

    def test_a_library_that_fails_to_load_is_shown_unavailable(self, backend: ScriptedMidiInput) -> None:
        backend.failing = True
        harness = Harness(backend, saved=KEYBOARD)
        harness.start()

        harness.coordinator.open()

        assert not harness.window.shown.available
        assert harness.window.shown.ports == ()


class TestKeysAndLosses:
    """The dialog names each key played while it stands, and a keyboard going away is told on the status bar."""

    def test_a_key_played_while_the_dialog_stands_is_named(self, harness: Harness) -> None:
        harness.start()
        harness.coordinator.open()
        harness.router.publish()

        harness.coordinator.heard(MidiNoteOn(note=MIDDLE_C, velocity=VELOCITY))

        assert harness.window.keys == [("C-3", VELOCITY)]

    def test_a_key_played_with_the_dialog_closed_names_nothing(self, harness: Harness) -> None:
        harness.start()
        harness.router.publish()

        harness.coordinator.heard(MidiNoteOn(note=MIDDLE_C, velocity=VELOCITY))

        assert harness.window.keys == []

    def test_a_keyboard_going_away_is_told_on_the_status_bar(
        self,
        harness: Harness,
        backend: ScriptedMidiInput,
    ) -> None:
        harness.start()

        backend.unplug(KEYBOARD)
        deadline = time.monotonic() + WAIT_SECONDS
        while not harness.posted:
            assert time.monotonic() < deadline, "the loss never reached the render thread"
            time.sleep(0.001)
        harness.run_posted()

        assert harness.statuses == [f"The MIDI keyboard {KEYBOARD} was disconnected."]
