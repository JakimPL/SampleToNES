import operator
from functools import partial
from typing import Final

from automation.screen import Screen
from automation.steps.main import home_path
from automation.vocabulary.converter import CONVERT_ONE, CONVERT_SEVERAL
from sampletones_application.tags.general import TAG_GLOBAL_THEME_STEMS_ROW, TAG_GLOBAL_THEME_STEMS_ROW_INERT
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.list.steps import gather
from tests.suite.screens.seeds.constants import KICK, SNARE

PLAY: Final[str] = "global.context.label.play"


class TestTheListComingAndGoing:
    """With nothing gathered the hint shows alone; the first recording brings the list, and removing the
    last one brings the hint back.
    """

    def test_the_hint_and_the_list_take_turns(self, screen: Screen) -> None:
        """The hint and the list swap places as recordings arrive and leave."""
        listing = screen.main.converter.list

        def the_hint_alone(screen: Screen) -> None:
            assert listing.hint_shown()
            assert not listing.list_shown()

        def the_first_recording_brings_the_list(screen: Screen) -> None:
            gather(screen, home_path(KICK))

            assert listing.list_shown()
            assert not listing.hint_shown()

        def removing_the_last_takes_it_away(screen: Screen) -> None:
            listing.remove(home_path(KICK))

            screen.expect(listing.hint_shown, bool, description="the hint back")
            assert not listing.list_shown()
            assert listing.rows() == []

        screen.scenario(the_hint_alone, the_first_recording_brings_the_list, removing_the_last_takes_it_away).run()


class TestUntickingEveryChannel:
    """A recording with every channel unticked reads as out of play and leaves the run count, and stays
    listed.
    """

    def test_the_row_dims_and_the_run_counts_without_it(self, screen: Screen) -> None:
        """The row takes the inert theme and the button counts one recording; ticking one channel restores
        both.
        """
        listing = screen.main.converter.list
        converter = screen.main.converter

        def gather_two(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))

            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        def untick_every_channel_of_one(screen: Screen) -> None:
            for channel in ChannelName:
                if listing.channel_ticked(home_path(KICK), channel):
                    listing.tick(home_path(KICK), channel)
                    screen.expect(
                        partial(listing.channel_ticked, home_path(KICK), channel),
                        operator.not_,
                        description=f"{channel} let go",
                    )

            screen.expect(
                partial(listing.row_theme, home_path(KICK)),
                TAG_GLOBAL_THEME_STEMS_ROW_INERT.__eq__,
                description="the row out of play",
            )
            assert converter.action() == screen.words(CONVERT_ONE).format(name=home_path(SNARE).stem)
            assert listing.has_row(home_path(KICK))

        def one_channel_brings_it_back(screen: Screen) -> None:
            listing.tick(home_path(KICK), ChannelName.PULSE1)

            screen.expect(
                partial(listing.row_theme, home_path(KICK)),
                TAG_GLOBAL_THEME_STEMS_ROW.__eq__,
                description="the row in play",
            )
            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        screen.scenario(gather_two, untick_every_channel_of_one, one_channel_brings_it_back).run()


class TestPlayingFromTheList:
    """A recording in the list plays on a double-click, and its menu leads with Play while the file exists."""

    def test_a_double_click_plays_and_play_greys_once_the_file_is_gone(self, screen: Screen) -> None:
        """Play is the first menu entry and turns disabled after the file is deleted from the disk."""
        listing = screen.main.converter.list
        menu = screen.context_menu

        def a_double_click_plays(screen: Screen) -> None:
            gather(screen, home_path(KICK))
            heard = screen.sound_heard()

            screen.hand.double_click(listing.row(home_path(KICK)))

            screen.expect(screen.sound_heard, heard.__lt__, description="the recording heard")
            assert listing.rows() == [listing.row(home_path(KICK))]

        def its_menu_leads_with_play(screen: Screen) -> None:
            screen.hand.right_click(listing.row(home_path(KICK)))
            screen.expect(menu.is_shown, bool, description="the menu")

            first = menu.entries()[0]

            assert (first.label, first.enabled) == (screen.words(PLAY), True)
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")

        def play_greys_once_the_file_is_gone(screen: Screen) -> None:
            home_path(KICK).unlink()

            screen.hand.right_click(listing.row(home_path(KICK)))
            screen.expect(menu.is_shown, bool, description="the menu again")

            first = menu.entries()[0]

            assert (first.label, first.enabled) == (screen.words(PLAY), False)
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away again")

        screen.scenario(a_double_click_plays, its_menu_leads_with_play, play_greys_once_the_file_is_gone).run()
