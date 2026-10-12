import operator
from typing import Final, List, Optional, Tuple

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import leave_letting_it_go, load_from_the_browser
from automation.views.instruments import read_takes_edits, read_words
from automation.vocabulary.instruments import NOTHING_LOADED, PREPARING
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, alternating_document_world

CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
REMOVED_KEY: Final[str] = "0"
TICKED_KEY: Final[str] = "1"

CardReading = Tuple[Optional[str], bool]


@pytest.fixture(name="world")
def world_fixture() -> World:
    """The home holds the two-minute reconstruction over three recordings taking turns."""
    return alternating_document_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The application opens with no reconstruction and no project."""
    return Startup(reconstruction=None, project=None)


class TestTheCardWhileTheSoundIsOnItsWay:
    """The instruments card keeps the bars it drew while the sound of a change is on its way, takes no edit of
    them meanwhile, and takes edits again once the sound lands.

    A document just opened has no bars yet, so the card says the instruments are being prepared,
    and never that nothing is loaded. A removal and a recording ticked away and back at once
    each send the sound and the envelopes to the worker. The scenario records the card's words and
    whether a sequence field takes edits after every frame through each gesture: the bars stay,
    the field is held for a while, and once the sound lands the field takes edits and the bars
    stand drawn.
    """

    def test_the_card_keeps_its_bars_and_holds_edits_until_the_sound_lands(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        stems = reconstructions.stems
        preparing = screen.words(PREPARING)
        nothing_loaded = screen.words(NOTHING_LOADED)
        watched: List[ChannelName] = []

        def drawn() -> Tuple[ChannelName, ...]:
            return tuple(channel for channel in CHANNELS if instruments.envelope(channel, FeatureKey.VOLUME))

        def read_card() -> CardReading:
            return (read_words(), read_takes_edits(watched[0], FeatureKey.VOLUME))

        def free_with_its_bars(screen: Screen) -> None:
            screen.expect(screen.sound_settled, bool, description="the sound landed")
            screen.expect(
                lambda: instruments.takes_edits(watched[0], FeatureKey.VOLUME),
                bool,
                description="the card taking edits",
            )
            assert instruments.says() is None
            assert drawn()

        def kept_and_held_meanwhile(readings: List[CardReading]) -> None:
            assert all(words is None for words, _ in readings), readings
            assert any(not takes_edits for _, takes_edits in readings), readings

        def open_it_reading_the_words(screen: Screen) -> None:
            assert instruments.says() == nothing_loaded

            with screen.record(read_words) as recording:
                load_from_the_browser(screen, LONG_RECONSTRUCTION)
                screen.expect(
                    lambda: reconstructions.shows_open(LONG_RECONSTRUCTION),
                    bool,
                    description=f"{LONG_RECONSTRUCTION.name} open",
                )
                screen.expect(screen.sound_settled, bool, description="the sound of the opening landed")

            seen = recording.values()
            assert preparing in seen, seen
            assert nothing_loaded not in seen[seen.index(preparing) :], seen
            screen.expect(drawn, bool, description="the bars drawn")
            watched.append(drawn()[0])
            free_with_its_bars(screen)

        def remove_one_keeping_the_bars(screen: Screen) -> None:
            stems.remove(REMOVED_KEY)
            screen.expect(stems.remove_prompt.is_shown, bool, description="the question about removing")

            with screen.record(read_card) as recording:
                stems.remove_prompt.confirm()
                screen.expect(lambda: stems.has_row(REMOVED_KEY), operator.not_, description="the recording gone")
                screen.expect(screen.sound_settled, bool, description="the sound of the rest landed")

            kept_and_held_meanwhile(recording.values())
            free_with_its_bars(screen)

        def tick_one_away_and_back_keeping_the_bars(screen: Screen) -> None:
            with screen.record(read_card) as recording:
                stems.tick(TICKED_KEY)
                stems.tick(TICKED_KEY)
                screen.expect(lambda: stems.hears(TICKED_KEY), bool, description="the recording heard again")
                screen.expect(screen.sound_settled, bool, description="the sound of the choice landed")

            kept_and_held_meanwhile(recording.values())
            free_with_its_bars(screen)

        screen.scenario(
            open_it_reading_the_words,
            remove_one_keeping_the_bars,
            tick_one_away_and_back_keeping_the_bars,
            leave_letting_it_go,
        ).run()
