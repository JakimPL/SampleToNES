import operator
from typing import Callable, Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.reconstructions.instruments.constants import NOTE_FRAMES, NOTHING, PIANO_C
from tests.screens.reconstructions.instruments.steps import give_it_a_volume
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.dearpygui.keys import IMGUI_DIGIT_ZERO, IMGUI_ESCAPE
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import leave_letting_the_project_go
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, SONG

PIANO_C_SHARP_UP: Final[int] = IMGUI_DIGIT_ZERO + 2
TOGGLE_PULSE_TWO: Final[ShortcutId] = ShortcutId.TOGGLE_CHANNEL_PULSE_2


class TestTheNoteKeys:
    """With an instrument open the note keys sound it, a field being typed in takes them as characters, and
    the keys a reconstruction gives a meaning keep it.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_keys_sound_the_instrument_and_a_field_keeps_them(self, screen: Screen) -> None:
        """Piano keys play sound; with the Arpeggio field focused, the same key writes its letter and plays
        nothing.
        """
        instruments = screen.reconstructions.instruments

        def sounded(key: int) -> bool:
            heard = screen.sound_heard()
            screen.hand.press_key(key, modifiers=[])
            screen.frames(NOTE_FRAMES)

            return screen.sound_heard() > heard

        def the_keys_sound_it(screen: Screen) -> None:
            give_it_a_volume(screen)

            assert sounded(PIANO_C)
            assert sounded(PIANO_C_SHARP_UP)

        def a_field_takes_them_as_characters(screen: Screen) -> None:
            field = instruments.field(ChannelName.PULSE1, FeatureKey.ARPEGGIO)
            screen.hand.scroll_into_view(field)
            screen.hand.click(field)

            assert not sounded(PIANO_C)
            assert "z" in instruments.envelope(ChannelName.PULSE1, FeatureKey.ARPEGGIO)

        screen.scenario(the_keys_sound_it, a_field_takes_them_as_characters, leave_letting_the_project_go).run()

    def test_undo_undoes_with_an_instrument_open(self, screen: Screen) -> None:
        """Undo removes the typed volume while the Reconstructions tab shows an instrument."""
        instruments = screen.reconstructions.instruments
        give_it_a_volume(screen)
        screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

        screen.press_shortcut(ShortcutId.UNDO)

        screen.expect(
            lambda: instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
            NOTHING.__eq__,
            description="the volume undone",
        )


class TestAChannelKeyOnAReconstruction:
    """With a reconstruction open, a channel's number key ticks its box above the waveform."""

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens a reconstruction and no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_two_lets_pulse_two_go_and_brings_it_back(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        expect_open(screen, OPEN_RECONSTRUCTION)
        assert reconstructions.channel_ticked(ChannelName.PULSE2)

        screen.press_shortcut(ShortcutId.TOGGLE_CHANNEL_PULSE_2)

        screen.expect(
            lambda: reconstructions.channel_ticked(ChannelName.PULSE2), operator.not_, description="Pulse 2 let go"
        )
        screen.press_shortcut(ShortcutId.TOGGLE_CHANNEL_PULSE_2)
        screen.expect(lambda: reconstructions.channel_ticked(ChannelName.PULSE2), bool, description="Pulse 2 back")


class TestAChannelChordBesideTheNoteKeys:
    """With an instrument open, Pulse 2's key plays a note, and its chord plays nothing.

    The waveform shows the instrument alone, so the chord finds no channel to switch. The key sounds a note,
    the chord then sounds nothing, and the key pressed once more sounds a note, which is what a chord that
    played would have done.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens the song with no reconstruction."""
        return Startup(reconstruction=None, project=SONG)

    def test_the_key_plays_and_the_chord_plays_nothing(self, screen: Screen) -> None:
        def sounded_over(press: Callable[[ShortcutId], None]) -> bool:
            heard = screen.sound_heard()
            press(TOGGLE_PULSE_TWO)
            screen.frames(NOTE_FRAMES)

            return screen.sound_heard() > heard

        def the_key_plays_a_note(screen: Screen) -> None:
            give_it_a_volume(screen)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)

            assert sounded_over(screen.press_shortcut)

        def the_chord_plays_nothing(screen: Screen) -> None:
            assert not sounded_over(screen.press_shortcut_alias)

        def the_key_still_plays(screen: Screen) -> None:
            assert sounded_over(screen.press_shortcut)

        screen.scenario(
            the_key_plays_a_note,
            the_chord_plays_nothing,
            the_key_still_plays,
            leave_letting_the_project_go,
        ).run()


class TestAChannelChordBesideAField:
    """While a field of a reconstruction's instrument is typed in, Pulse 2's key types its digit, and its chord
    switches Pulse 2 above the waveform all the same.

    The key types a digit into Pulse 1's Volume field and leaves Pulse 2 ticked. The chord then lets Pulse 2
    go and leaves the field as it read, the chord again brings Pulse 2 back, and the key types once more into
    the field, which is where a chord that typed would have written.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """The application opens a reconstruction sounding every channel and no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_key_types_and_the_chord_switches_pulse_two(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        typed: List[str] = []

        def volume() -> str:
            return instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME)

        def pulse_two_ticked() -> bool:
            return reconstructions.channel_ticked(ChannelName.PULSE2)

        def the_key_types_its_digit(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            screen.tabs.bring_to_front(Tab.RECONSTRUCTIONS)
            instruments.bring_forward(ChannelName.PULSE1)
            field = instruments.field(ChannelName.PULSE1, FeatureKey.VOLUME)
            screen.hand.scroll_into_view(field)
            screen.hand.click(field)
            before = volume()

            screen.press_shortcut(TOGGLE_PULSE_TWO)

            typed.append(screen.expect(volume, before.__ne__, description="a digit typed into the field"))
            assert pulse_two_ticked()

        def the_chord_lets_pulse_two_go_and_types_nothing(screen: Screen) -> None:
            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(pulse_two_ticked, operator.not_, description="Pulse 2 let go")
            screen.frames(NOTE_FRAMES)
            assert volume() == typed[0]

        def the_chord_brings_it_back(screen: Screen) -> None:
            screen.press_shortcut_alias(TOGGLE_PULSE_TWO)

            screen.expect(pulse_two_ticked, bool, description="Pulse 2 back")

        def the_key_types_into_the_field_again(screen: Screen) -> None:
            screen.press_shortcut(TOGGLE_PULSE_TWO)

            screen.expect(volume, typed[0].__ne__, description="a second digit typed into the field")
            assert pulse_two_ticked()
            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])

        screen.scenario(
            the_key_types_its_digit,
            the_chord_lets_pulse_two_go_and_types_nothing,
            the_chord_brings_it_back,
            the_key_types_into_the_field_again,
        ).run()
