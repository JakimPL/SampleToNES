import operator
from functools import partial
from typing import Final

import pytest

from automation.screen import Screen
from automation.steps.main import gather, home_path
from automation.worlds.home import World, lived_in_world
from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL
from tests.screens.main.row_settings.constants import FREQUENCY
from tests.suite.screens.seeds.recordings import Recording

HUNDREDS: Final[str] = "Hundreds"
HUNDREDS_COUNT: Final[int] = 300
TINY_SECONDS: Final[float] = 0.01


class TestHundredsGathered:
    """Some three hundred recordings gathered: the card collapses and expands, the interface answers
    meanwhile, and the list scrolls end to end.

    The folder is gathered and the card collapsed. The Sequencer and the Main tab are brought to the
    front in turn. The card is then expanded, the folder opened and the list scrolled to its end, where
    the last row is drawn and hovered.
    """

    @pytest.fixture
    def world(self) -> World:
        """A lived-in home holding a folder of three hundred very short recordings."""
        files = tuple(
            Recording(
                destination=home_path(HUNDREDS) / f"take{index:03d}.wav", seconds=TINY_SECONDS, frequency=FREQUENCY
            )
            for index in range(HUNDREDS_COUNT)
        )
        return World(state=lived_in_world().state, application_config=None, config=None, files=files)

    def test_collapse_expand_and_scroll_end_to_end(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        card = main.card(TAG_MAIN_CONVERTER_PANEL)
        folder = home_path(HUNDREDS)
        last = folder / f"take{HUNDREDS_COUNT - 1:03d}.wav"

        def gather_and_collapse(screen: Screen) -> None:
            gather(screen, folder)
            card.toggle()

            screen.expect(card.is_collapsed, bool, description="the card collapsed")

        def the_interface_answers_meanwhile(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer in front")
            screen.tabs.bring_to_front(Tab.MAIN)
            screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab back")

        def expand_and_scroll_end_to_end(screen: Screen) -> None:
            card.toggle()
            screen.expect(card.is_collapsed, operator.not_, description="the card open")
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

            screen.hand.scroll_to_end(listing.tags.region(str(folder)))

            screen.expect(partial(listing.has_row, last), bool, description="the last row drawn")
            screen.hand.scroll_into_view(listing.row(last))
            screen.hand.hover(listing.row(last))

        screen.scenario(gather_and_collapse, the_interface_answers_meanwhile, expand_and_scroll_end_to_end).run()
