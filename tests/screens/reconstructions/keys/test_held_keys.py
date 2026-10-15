import dataclasses
from typing import Final, Optional, Tuple

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.project import leave_letting_the_project_go
from automation.steps.reconstructions import expect_open
from automation.worlds.home import World
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.midi import MidiConfig
from tests.screens.reconstructions.instruments.constants import NOTE_FRAMES, PIANO_C
from tests.screens.reconstructions.instruments.steps import give_it_a_volume
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION, SONG, playing_world

KEYBOARD: Final[str] = "Test Keyboard"
MIDDLE_C_ON: Final[bytes] = bytes((0x90, 60, 100))
MIDDLE_C_OFF: Final[bytes] = bytes((0x80, 60, 0))


def _sounding_over(screen: Screen, frames: int) -> bool:
    """Whether the device took sound over the next ``frames`` frames."""
    heard = screen.sound_heard()
    screen.frames(frames)
    return screen.sound_heard() > heard


def _silent_over(screen: Screen, frames: int) -> bool:
    """Whether the device took no sound over the next ``frames`` frames."""
    return not _sounding_over(screen, frames)


def _mark(screen: Screen) -> Optional[float]:
    return screen.reconstructions.waveform.cursor()


class TestAHeldPianoKey:
    """A piano key held over an open instrument holds its sound, and the release silences it.

    The song's instrument gets a volume that holds its last level, so its note sounds for as long as a key is
    down. While the key stays down the device keeps taking sound and the plot card's mark follows the note;
    once the key lifts the sound stops and the mark comes off, though the stream stays open a while.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_a_held_key_holds_the_sound_and_its_release_silences_it(self, screen: Screen) -> None:
        def hold_a_key(screen: Screen) -> None:
            give_it_a_volume(screen)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            screen.hand.hold_key(PIANO_C)

            assert screen.expect(lambda: _sounding_over(screen, NOTE_FRAMES), bool, description="the note heard")

        def the_note_holds(screen: Screen) -> None:
            assert _sounding_over(screen, NOTE_FRAMES)
            assert _sounding_over(screen, NOTE_FRAMES)
            screen.expect(lambda: _mark(screen), lambda mark: mark is not None and mark > 0, description="the mark")

        def lift_the_key(screen: Screen) -> None:
            screen.hand.lift_key(PIANO_C)

            screen.expect(lambda: _silent_over(screen, NOTE_FRAMES), bool, description="the note silenced")
            screen.expect(lambda: _mark(screen), lambda mark: mark is None, description="the mark taken off")

        screen.scenario(hold_a_key, the_note_holds, lift_the_key, leave_letting_the_project_go).run()


class TestAMidiKeyOnARecording:
    """A MIDI key plays the recording in front of the Reconstructions tab, and cuts it as it lifts.

    The keyboard the session kept is read as the application starts. With the Main tab in front a key sounds
    nothing; with the Reconstructions tab in front a key held plays the recording, and its release silences it
    before the recording ends.
    """

    @pytest.fixture
    def world(self) -> World:
        """The playing home, whose settings keep the keyboard."""
        return dataclasses.replace(
            playing_world(),
            application_config=ApplicationConfig(midi=MidiConfig(port=KEYBOARD)),
        )

    @pytest.fixture
    def midi_keyboards(self) -> Tuple[str, ...]:
        return (KEYBOARD,)

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=PLAYABLE_RECONSTRUCTION, project=None)

    def test_a_key_plays_the_recording_on_its_tab_alone(self, screen: Screen) -> None:
        def struck_and_heard(screen: Screen) -> bool:
            """Strikes middle C again and reads whether it sounds; a key arriving as the port opens stays silent."""
            screen.play_midi(KEYBOARD, MIDDLE_C_ON)
            return _sounding_over(screen, NOTE_FRAMES)

        def another_tab_hears_nothing(screen: Screen) -> None:
            expect_open(screen, PLAYABLE_RECONSTRUCTION)
            screen.expect(screen.midi_ports_opened, (KEYBOARD,).__eq__, description="the kept keyboard read")
            screen.tabs.bring_to_front(Tab.MAIN)
            screen.frames(NOTE_FRAMES)

            screen.play_midi(KEYBOARD, MIDDLE_C_ON)

            assert _silent_over(screen, NOTE_FRAMES)
            screen.play_midi(KEYBOARD, MIDDLE_C_OFF)

        def its_tab_plays_the_recording(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            screen.expect(lambda: struck_and_heard(screen), bool, description="the recording heard")

        def the_release_cuts_it(screen: Screen) -> None:
            """The recording plays on for seconds after the release, so silence within a few frames is the cut."""
            screen.play_midi(KEYBOARD, MIDDLE_C_OFF)
            screen.frames(NOTE_FRAMES)

            assert _silent_over(screen, NOTE_FRAMES)

        screen.scenario(another_tab_hears_nothing, its_tab_plays_the_recording, the_release_cuts_it).run()
