from typing import Final, Tuple

import pytest

from automation.screen import Screen
from automation.worlds.home import World, screen_filling_state
from automation.written import written_application_config
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.midi import MidiConfig
from tests.screens.application.restart.steps import leave

KEYBOARD: Final[str] = "Test Keyboard"
OTHER: Final[str] = "Other Keyboard"
MIDDLE_C: Final[bytes] = bytes((0x90, 60, 100))
MIDDLE_C_READING: Final[Tuple[str, str]] = ("C-3", "100")
UNREAD: Final[Tuple[str, str]] = ("", "")
NO_INPUT: Final[str] = "settings.midi.label.no_input"
PLAY_A_KEY: Final[str] = "settings.midi.message.play_a_key"
UNAVAILABLE: Final[str] = "settings.midi.message.unavailable"


def _named_after_playing(screen: Screen, keyboard: str) -> Tuple[str, str]:
    """Plays middle C on ``keyboard`` and reads the key played last with its velocity.

    A port drops what arrives as it opens, so a key played that early stays unnamed; the reading plays again on
    each frame until the dialog names it.
    """
    screen.play_midi(keyboard, MIDDLE_C)
    return screen.midi_settings.last_key()


def _opened(screen: Screen) -> None:
    screen.midi_settings.open()
    screen.expect(screen.midi_settings.is_shown, bool, description="the MIDI settings dialog")


def _canceled(screen: Screen) -> None:
    screen.midi_settings.cancel()
    screen.expect(screen.midi_settings.is_shown, lambda shown: not shown, description="the dialog closed")


class TestAKeyboardKeptByTheSession:
    """The keyboard the session kept is read as the application starts, and the dialog names it."""

    @pytest.fixture
    def midi_keyboards(self) -> Tuple[str, ...]:
        return (KEYBOARD,)

    @pytest.fixture
    def world(self) -> World:
        """A home whose settings keep the keyboard."""
        return World(
            state=screen_filling_state(),
            application_config=ApplicationConfig(midi=MidiConfig(port=KEYBOARD)),
            config=None,
            files=(),
        )

    def test_the_kept_keyboard_is_read_as_the_application_starts(self, screen: Screen) -> None:
        screen.expect(screen.midi_ports_opened, (KEYBOARD,).__eq__, description="the kept keyboard read")

        _opened(screen)
        named = screen.midi_settings.input()
        _canceled(screen)

        assert named == KEYBOARD


class TestPickingAKeyboard:
    """The dialog lists the keyboards, reads the one picked at once, and OK keeps it for the next run."""

    @pytest.fixture
    def midi_keyboards(self) -> Tuple[str, ...]:
        return (KEYBOARD, OTHER)

    def test_the_dialog_lists_every_keyboard_after_none(self, screen: Screen) -> None:
        _opened(screen)
        inputs, named = screen.midi_settings.inputs(), screen.midi_settings.input()
        _canceled(screen)

        assert inputs == (screen.words(NO_INPUT), KEYBOARD, OTHER)
        assert named == screen.words(NO_INPUT)
        assert screen.midi_ports_opened() == ()

    def test_a_key_played_on_the_picked_keyboard_is_named(self, screen: Screen) -> None:
        _opened(screen)

        screen.midi_settings.choose_input(KEYBOARD)
        before = screen.midi_settings.message(), screen.midi_settings.last_key()

        screen.expect(
            lambda: _named_after_playing(screen, KEYBOARD),
            MIDDLE_C_READING.__eq__,
            description="the key named",
        )
        _canceled(screen)

        assert before == (screen.words(PLAY_A_KEY), UNREAD)

    def test_ok_keeps_the_keyboard_for_the_next_run(self, screen: Screen) -> None:
        _opened(screen)
        screen.midi_settings.choose_input(KEYBOARD)

        screen.midi_settings.confirm()
        screen.expect(screen.midi_settings.is_shown, lambda shown: not shown, description="the dialog closed")
        leave(screen)

        assert written_application_config().midi.port == KEYBOARD

    def test_cancel_keeps_no_keyboard_though_one_was_read(self, screen: Screen) -> None:
        _opened(screen)
        screen.midi_settings.choose_input(KEYBOARD)

        _canceled(screen)
        leave(screen)

        assert screen.midi_ports_opened() == (KEYBOARD,)
        assert written_application_config().midi.port is None


class TestAMachineWithoutMidi:
    """On a machine offering no MIDI library the dialog says so in one line, and OK closes it."""

    @pytest.fixture
    def midi_library_loads(self) -> bool:
        return False

    def test_the_dialog_says_midi_is_unavailable(self, screen: Screen) -> None:
        _opened(screen)
        line = screen.midi_settings.unavailable_line()

        screen.midi_settings.confirm()
        screen.expect(screen.midi_settings.is_shown, lambda shown: not shown, description="the dialog closed")

        assert line == screen.words(UNAVAILABLE)
