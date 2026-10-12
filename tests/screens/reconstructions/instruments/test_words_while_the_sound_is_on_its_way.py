import operator
from typing import Final, List, Optional, Tuple

import pytest

from automation.application.startup import Startup
from automation.screen import Screen
from automation.steps.reconstructions import leave_letting_it_go, load_from_the_browser
from automation.views.instruments import read_words
from automation.vocabulary.instruments import NOTHING_LOADED, PREPARING
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, alternating_document_world

CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
RECORDING_KEY: Final[str] = "0"


@pytest.fixture(name="world")
def world_fixture() -> World:
    """The home holds the two-minute reconstruction over three recordings taking turns."""
    return alternating_document_world()


@pytest.fixture(name="startup")
def startup_fixture() -> Startup:
    """The application opens with no reconstruction and no project."""
    return Startup(reconstruction=None, project=None)


class TestTheWordsWhileTheSoundIsOnItsWay:
    """The instruments card says the instruments are being prepared while a document's envelopes are rendered,
    and from the moment a document is open it never says none is loaded.

    An opening and a removal send the envelopes to the worker with the sound, so the card has no bars to
    draw until they land. The scenario records the card's words after every frame through the opening of
    the two-minute document and through the removal of one of its recordings. Each time the words say the
    instruments are being prepared, the words saying nothing is loaded never follow them, and the bars
    come with the sound.
    """

    def test_the_card_says_what_is_on_its_way_and_then_draws_it(self, screen: Screen) -> None:
        reconstructions = screen.reconstructions
        instruments = reconstructions.instruments
        stems = reconstructions.stems
        preparing = screen.words(PREPARING)
        nothing_loaded = screen.words(NOTHING_LOADED)

        def drawn() -> Tuple[ChannelName, ...]:
            return tuple(channel for channel in CHANNELS if instruments.envelope(channel, FeatureKey.VOLUME))

        def the_tabs_stand(screen: Screen) -> None:
            screen.expect(instruments.says, operator.not_, description="the tabs standing")
            assert screen.expect(drawn, bool, description="the bars drawn")

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

            seen: List[Optional[str]] = recording.values()
            assert preparing in seen, seen
            assert nothing_loaded not in seen[seen.index(preparing) :], seen
            the_tabs_stand(screen)

        def remove_one_reading_the_words(screen: Screen) -> None:
            stems.remove(RECORDING_KEY)
            screen.expect(stems.remove_prompt.is_shown, bool, description="the question about removing")

            with screen.record(read_words) as recording:
                stems.remove_prompt.confirm()
                screen.expect(lambda: stems.has_row(RECORDING_KEY), operator.not_, description="the recording gone")
                screen.expect(screen.sound_settled, bool, description="the sound of the rest landed")

            seen = recording.values()
            assert preparing in seen, seen
            assert nothing_loaded not in seen, seen
            the_tabs_stand(screen)

        screen.scenario(open_it_reading_the_words, remove_one_reading_the_words, leave_letting_it_go).run()
