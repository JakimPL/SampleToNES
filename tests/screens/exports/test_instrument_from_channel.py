import operator
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters.naming import instrument_slice_name
from tests.suite.screens.application import Startup
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import voice_title
from tests.suite.screens.steps.sequencer import forgive_the_hover_race, open_voice, open_voice_menu
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_VOICE, LINE, PAD

INSTRUMENT_FROM: Final[str] = "sequencer.voices.label.context_instrument_from"
LINE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)
INSTRUMENT_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
VOICES: Final[List[str]] = [LINE, BASS_VOICE, PAD]


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


def leaving_asks_nothing(screen: Screen) -> None:
    """Exits a project every change of which was undone, which leaves at once."""
    forgive_the_hover_race(screen)
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


class TestTheSubmenuNamesTheChannelsThatPlay:
    """New instrument from names each channel a sample plays, one channel among them; a hand-written voice greys it."""

    def test_each_channel_one_channel_and_none(self, screen: Screen) -> None:
        menu = screen.context_menu

        def a_sample_of_three_channels_names_each(screen: Screen) -> None:
            open_voice_menu(screen, LINE)

            assert menu.submenu(screen.words(INSTRUMENT_FROM)) == [
                (screen.channel_words(channel), True) for channel in LINE_CHANNELS
            ]
            menu.dismiss()

        def a_sample_of_one_channel_still_names_it(screen: Screen) -> None:
            open_voice_menu(screen, BASS_VOICE)

            assert menu.submenu(screen.words(INSTRUMENT_FROM)) == [(screen.channel_words(ChannelName.TRIANGLE), True)]
            assert screen.words(INSTRUMENT_FROM) not in menu.labels()
            menu.dismiss()

        def a_hand_written_voice_greys_it(screen: Screen) -> None:
            open_voice_menu(screen, PAD)

            assert screen.words(INSTRUMENT_FROM) not in menu.submenus()
            entry = next(entry for entry in menu.entries() if entry.label == screen.words(INSTRUMENT_FROM))
            assert not entry.enabled
            menu.dismiss()

        screen.scenario(
            a_sample_of_three_channels_names_each,
            a_sample_of_one_channel_still_names_it,
            a_hand_written_voice_greys_it,
            leaving_asks_nothing,
        ).run()


class TestTakingAChannel:
    """Taking a channel adds `<sample> (<channel>)` carrying that channel's envelopes and opens it; one undo takes it
    away and leaves the sample as it was.

    The undo is the History card's, since the note keys of the instrument left open take Ctrl+Z (bugs-and-todos §
    Bugs).
    """

    def test_each_channel_of_the_line(self, screen: Screen) -> None:
        voices = screen.sequencer.voices
        instruments = screen.reconstructions.instruments
        played: Dict[ChannelName, str] = {}

        def read_what_each_channel_plays(screen: Screen) -> None:
            open_voice(screen, LINE)
            screen.expect(
                lambda: instruments.tab_shown(ChannelName.NOISE),
                bool,
                description="the line's channels",
            )

            for channel in LINE_CHANNELS:
                played[channel] = instruments.envelope(channel, FeatureKey.VOLUME)

        def taking(channel: ChannelName) -> None:
            name = instrument_slice_name(LINE, channel)
            open_voice_menu(screen, LINE)

            screen.context_menu.choose_in(screen.words(INSTRUMENT_FROM), screen.channel_words(channel))

            screen.expect(voices.names, (VOICES + [name]).__eq__, description=f"{name} listed")
            screen.expect(
                lambda: instruments.tab_label(INSTRUMENT_CHANNEL),
                name.__eq__,
                description=f"{name} open",
            )
            assert screen.tabs.front() == Tab.RECONSTRUCTIONS
            assert instruments.offers_audition()
            assert instruments.envelope(INSTRUMENT_CHANNEL, FeatureKey.VOLUME) == played[channel]

            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.sequencer.history.undo()

            screen.expect(voices.names, VOICES.__eq__, description=f"{name} taken away")

        def take_each_channel_and_undo_it(screen: Screen) -> None:
            for channel in LINE_CHANNELS:
                taking(channel)

        def the_line_plays_as_it_did(screen: Screen) -> None:
            open_voice(screen, LINE)
            screen.expect(
                lambda: instruments.tab_shown(ChannelName.NOISE),
                bool,
                description="the line's channels",
            )

            assert {channel: instruments.envelope(channel, FeatureKey.VOLUME) for channel in LINE_CHANNELS} == played
            screen.expect(
                screen.title,
                voice_title(screen, ARRANGED_PROJECT.stem, 0, LINE, unsaved=False).__eq__,
                description="the project as it was",
            )

        screen.scenario(
            read_what_each_channel_plays,
            take_each_channel_and_undo_it,
            the_line_plays_as_it_did,
            leaving_asks_nothing,
        ).run()
