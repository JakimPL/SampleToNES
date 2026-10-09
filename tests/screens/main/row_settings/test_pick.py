import operator
from functools import partial
from typing import Final

from automation.screen import Screen
from automation.steps.main import gather, home_path
from automation.vocabulary.converter import FOLDER_ROW
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.constants import PAIR, PAIR_TAKES
from tests.screens.main.row_settings.steps import ticked
from tests.suite.screens.seeds.constants import KICK, SNARE

NEW_RECORDINGS: Final[str] = "main.source.label.new_recordings"


class TestTheCardFollowsThePick:
    """Source settings names the picked row, recording or folder, and reads New recordings while no row is
    picked.
    """

    def test_it_names_each_pick_in_turn(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list

        def nothing_picked(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(PAIR))

            assert main.source.subject() == screen.words(NEW_RECORDINGS)

        def a_recording_picked(screen: Screen) -> None:
            listing.pick(home_path(KICK))

            screen.expect(main.source.subject, home_path(KICK).stem.__eq__, description="the recording named")
            assert listing.is_picked(home_path(KICK))
            assert {channel: main.source.channel_ticked(channel) for channel in ChannelName} == ticked(
                screen, home_path(KICK)
            )

        def a_folder_picked(screen: Screen) -> None:
            listing.pick(home_path(PAIR))

            expected = screen.words(FOLDER_ROW).format(name=PAIR, count=len(PAIR_TAKES))
            screen.expect(main.source.subject, expected.__eq__, description="the folder named")
            assert not listing.is_picked(home_path(KICK))

        screen.scenario(nothing_picked, a_recording_picked, a_folder_picked).run()


class TestThePickHoldsThrough:
    """The pick stands through a second click, a double-click that plays the row, and Esc stopping it.

    The kick is picked twice, then double-clicked so that it plays, then Esc stops playback. After each
    gesture the kick is still the picked row and the card still names it.
    """

    def test_clicks_double_clicks_and_esc_keep_the_pick(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        playback = screen.sequencer.playback

        def pick_twice(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))
            listing.pick(home_path(KICK))
            screen.expect(partial(listing.is_picked, home_path(KICK)), bool, description="picked")

            listing.pick(home_path(KICK))

            assert listing.is_picked(home_path(KICK))
            assert main.source.subject() == home_path(KICK).stem

        def a_double_click_plays_and_keeps_it(screen: Screen) -> None:
            heard = screen.sound_heard()
            screen.hand.double_click(listing.row(home_path(KICK)))

            screen.expect(screen.sound_heard, heard.__lt__, description="the recording heard")
            assert listing.is_picked(home_path(KICK))

        def esc_stops_and_keeps_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)

            screen.expect(playback.can_stop, operator.not_, description="playback stopped")
            assert listing.is_picked(home_path(KICK))
            assert main.source.subject() == home_path(KICK).stem

        screen.scenario(pick_twice, a_double_click_plays_and_keeps_it, esc_stops_and_keeps_it).run()


class TestARightClickMovesThePick:
    """A right-click on a row picks it, and Del then removes that row.

    The kick is picked and the snare right-clicked. The card names the snare and the menu is put away;
    Del then removes the snare and leaves the kick.
    """

    def test_del_after_a_right_click_removes_the_row_clicked(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        menu = screen.context_menu

        def right_click_another_row(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))
            listing.pick(home_path(KICK))

            screen.hand.right_click(listing.row(home_path(SNARE)))

            screen.expect(menu.is_shown, bool, description="the menu")
            screen.expect(main.source.subject, home_path(SNARE).stem.__eq__, description="the card on the row clicked")
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")

        def del_removes_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)

            screen.expect(partial(listing.has_row, home_path(SNARE)), operator.not_, description="the row removed")
            assert listing.rows() == [listing.row(home_path(KICK))]

        screen.scenario(right_click_another_row, del_removes_it).run()
