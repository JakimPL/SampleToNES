import operator
from typing import Final

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.reconstructions.instruments.constants import NOTE_FRAMES, NOTHING, PIANO_C
from tests.screens.reconstructions.instruments.steps import give_it_a_volume
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.dearpygui.keys import IMGUI_DIGIT_ZERO
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import leave_letting_the_project_go
from tests.suite.screens.steps.reconstructions import expect_open
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, SONG

PIANO_C_SHARP_UP: Final[int] = IMGUI_DIGIT_ZERO + 2


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
