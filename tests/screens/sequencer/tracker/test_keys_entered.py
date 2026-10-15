import dataclasses
from typing import Final, Tuple

import pytest

from automation.dearpygui.keys import IMGUI_ESCAPE
from automation.screen import Screen
from automation.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.midi import MidiConfig
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import velocity_level
from sampletones_core.project.patterns.pitch import Note
from sampletones_core.utils.display import display_pitch, display_volume
from tests.screens.sequencer.tracker.constants import PIANO_C, TYPING_FRAMES
from tests.suite.screens.worlds.songs import PAD_ROW, sequencer_world

KEYBOARD: Final[str] = "Test Keyboard"
STRUCK_NOTE: Final[int] = 64
VELOCITY: Final[int] = 70
NOTE_ON: Final[bytes] = bytes((0x90, STRUCK_NOTE, VELOCITY))
NOTE_OFF: Final[bytes] = bytes((0x80, STRUCK_NOTE, 0))
SETTLE_FRAMES: Final[int] = 30
NOTE_FRAMES: Final[int] = 30
CHANNEL: Final[ChannelName] = ChannelName.PULSE2


def _pitch_label(screen: Screen) -> str:
    return screen.sequencer.tracker.label(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)


def _sounding_over(screen: Screen, frames: int) -> bool:
    heard = screen.sound_heard()
    screen.frames(frames)
    return screen.sound_heard() > heard


def _struck(screen: Screen) -> None:
    """Plays the struck note on the keyboard and lets the frames that write it pass."""
    screen.play_midi(KEYBOARD, NOTE_ON)
    screen.frames(TYPING_FRAMES)
    screen.play_midi(KEYBOARD, NOTE_OFF)
    screen.frames(TYPING_FRAMES)


def _written(screen: Screen) -> bool:
    return _pitch_label(screen) == display_pitch(Note(value=STRUCK_NOTE))


@pytest.fixture
def world() -> World:
    """The Sequencer's home, whose settings keep the keyboard, its velocity setting the volume."""
    return dataclasses.replace(
        sequencer_world(),
        application_config=ApplicationConfig(midi=MidiConfig(port=KEYBOARD, velocity_sets_volume=True)),
    )


@pytest.fixture
def midi_keyboards() -> Tuple[str, ...]:
    return (KEYBOARD,)


def _ready(screen: Screen) -> None:
    on_the_sequencer(screen)
    screen.expect(screen.midi_ports_opened, (KEYBOARD,).__eq__, description="the kept keyboard read")
    screen.frames(SETTLE_FRAMES)


class TestAMidiNoteAtTheCaret:
    """A MIDI key at the caret's pitch writes its note and the volume it was struck at, and sounds the row.

    The caret stands on the pad's pitch. The key held writes the note and its level and sounds the pad, the
    caret steps down a row, and the key's release silences the row.
    """

    def test_a_key_writes_its_note_and_volume_and_sounds_the_row(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def hold_a_key_at_the_pitch(screen: Screen) -> None:
            _ready(screen)
            tracker.click(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)

            screen.play_midi(KEYBOARD, NOTE_ON)

            screen.expect(lambda: _written(screen), bool, description="the note written")
            assert tracker.label(PAD_ROW, CHANNEL, SubColumn.VOLUME) == display_volume(
                velocity_level(CHANNEL, VELOCITY)
            )
            assert tracker.has_caret(PAD_ROW + 1, CHANNEL)
            assert screen.expect(lambda: _sounding_over(screen, NOTE_FRAMES), bool, description="the row heard")

        def release_it(screen: Screen) -> None:
            screen.play_midi(KEYBOARD, NOTE_OFF)

            screen.expect(lambda: not _sounding_over(screen, NOTE_FRAMES), bool, description="the row silenced")

        screen.scenario(hold_a_key_at_the_pitch, release_it, leave_letting_the_project_go).run()


class TestWhereAMidiNoteWritesNothing:
    """Off the pitch slot, under a dialog and on another tab a key writes nothing; back at the pitch it does."""

    def test_a_key_writes_only_at_the_pitch_on_its_tab(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def off_the_pitch(screen: Screen) -> None:
            _ready(screen)
            tracker.click(PAD_ROW, CHANNEL, SubColumn.VOLUME)

            _struck(screen)

            assert not _written(screen)

        def under_a_dialog(screen: Screen) -> None:
            """A dialog other than the MIDI settings takes no key itself, so the grid is what must hold off."""
            tracker.click(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)
            screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
            screen.expect(screen.audio_settings.is_shown, bool, description="Audio settings")

            _struck(screen)
            written = _written(screen)
            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])
            screen.expect(screen.audio_settings.is_shown, lambda shown: not shown, description="the dialog closed")

            assert not written

        def on_another_tab(screen: Screen) -> None:
            tracker.click(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            _struck(screen)
            on_the_sequencer(screen)

            assert not _written(screen)

        def back_at_the_pitch(screen: Screen) -> None:
            tracker.click(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)

            _struck(screen)

            assert _written(screen)

        screen.scenario(
            off_the_pitch, under_a_dialog, on_another_tab, back_at_the_pitch, leave_letting_the_project_go
        ).run()


class TestAHeldPianoKeyInTheTracker:
    """A piano key held at the caret's pitch writes its note once and sounds the row until it lifts.

    The pad holds its last level, so the row sounds for as long as the key is down; the key's repeats write
    nothing more, and the release silences the row.
    """

    @pytest.fixture
    def midi_keyboards(self) -> Tuple[str, ...]:
        return ()

    @pytest.fixture
    def world(self) -> World:
        return sequencer_world()

    def test_a_held_key_sounds_the_row_it_wrote(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def hold_the_key(screen: Screen) -> None:
            on_the_sequencer(screen)
            tracker.click(PAD_ROW, CHANNEL, SubColumn.TRANSPOSE)

            screen.hand.hold_key(PIANO_C)

            assert screen.expect(lambda: _sounding_over(screen, NOTE_FRAMES), bool, description="the row heard")
            assert _sounding_over(screen, NOTE_FRAMES)
            assert tracker.has_caret(PAD_ROW + 1, CHANNEL)

        def lift_it(screen: Screen) -> None:
            screen.hand.lift_key(PIANO_C)

            screen.expect(lambda: not _sounding_over(screen, NOTE_FRAMES), bool, description="the row silenced")

        screen.scenario(hold_the_key, lift_it, leave_letting_the_project_go).run()
