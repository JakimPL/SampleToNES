import operator
from functools import partial
from typing import Dict, Final, List

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_INPUT_SEARCH
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL, TAG_MAIN_EXPLORER_PANEL
from sampletones_application.utils.gui.shortcuts.ids import CHANNEL_SHORTCUT_IDS, ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.steps import ticked
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import gather, home_path
from tests.suite.screens.vocabulary.recordings import KICK, SNARE

FILTER_TEXT: Final[str] = "zz"


class TestAChannelKey:
    """A channel's key settles that channel on the picked row alone; with nothing picked it changes nothing.

    Two recordings are gathered and Pulse 2 is pressed with nothing picked. The kick is then picked and
    the key pressed again; the kick's Pulse 2 flips once and the snare keeps its boxes.
    """

    def test_it_reaches_the_picked_row_alone(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        before: List[Dict[ChannelName, bool]] = []

        def press_with_nothing_picked(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))
            before.extend((ticked(screen, home_path(KICK)), ticked(screen, home_path(SNARE))))

            screen.press_shortcut(CHANNEL_SHORTCUT_IDS[ChannelName.PULSE2])

        def press_with_a_row_picked(screen: Screen) -> None:
            listing.pick(home_path(KICK))

            screen.press_shortcut(CHANNEL_SHORTCUT_IDS[ChannelName.PULSE2])

            expected = {**before[0], ChannelName.PULSE2: not before[0][ChannelName.PULSE2]}
            screen.expect(lambda: ticked(screen, home_path(KICK)), expected.__eq__, description="Pulse 2 flipped once")
            assert ticked(screen, home_path(SNARE)) == before[1]

        screen.scenario(press_with_nothing_picked, press_with_a_row_picked).run()


class TestTheKeysOfTheList:
    """Del and the channel keys reach the picked row while the Converter card is open and no field holds
    the keys.
    """

    def test_a_collapsed_card_keeps_del_from_the_list(self, screen: Screen) -> None:
        """Del leaves both rows in place while the card is collapsed and removes the picked row once open."""
        main = screen.main
        listing = main.converter.list
        card = main.card(TAG_MAIN_CONVERTER_PANEL)

        def del_with_the_card_collapsed(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))
            listing.pick(home_path(KICK))
            card.toggle()
            screen.expect(card.is_collapsed, bool, description="the card collapsed")

            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)

        def del_with_the_card_open(screen: Screen) -> None:
            card.toggle()
            screen.expect(card.is_collapsed, operator.not_, description="the card open")
            listing.pick(home_path(SNARE))

            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)

            screen.expect(partial(listing.has_row, home_path(SNARE)), operator.not_, description="the row removed")
            assert listing.rows() == [listing.row(home_path(KICK))]

        screen.scenario(del_with_the_card_collapsed, del_with_the_card_open).run()

    def test_a_focused_field_takes_del_and_the_channel_keys(self, screen: Screen) -> None:
        """Keys typed into the explorer's filter field stay in the field; once the field lets go, the same key
        reaches the picked row.
        """
        main = screen.main
        listing = main.converter.list
        field = compose_tag(TAG_MAIN_EXPLORER_PANEL, SUF_INPUT_SEARCH)
        before: List[Dict[ChannelName, bool]] = []

        def keys_into_the_field(screen: Screen) -> None:
            gather(screen, home_path(KICK))
            listing.pick(home_path(KICK))
            before.append(ticked(screen, home_path(KICK)))
            screen.hand.click(field)
            screen.hand.type_text(FILTER_TEXT)

            screen.press_shortcut(CHANNEL_SHORTCUT_IDS[ChannelName.PULSE2])
            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)

        def the_same_key_reaches_the_row_once_the_field_lets_go(screen: Screen) -> None:
            listing.pick(home_path(KICK))

            screen.press_shortcut(CHANNEL_SHORTCUT_IDS[ChannelName.PULSE2])

            expected = {**before[0], ChannelName.PULSE2: not before[0][ChannelName.PULSE2]}
            screen.expect(lambda: ticked(screen, home_path(KICK)), expected.__eq__, description="Pulse 2 flipped")
            assert listing.rows() == [listing.row(home_path(KICK))]

        screen.scenario(keys_into_the_field, the_same_key_reaches_the_row_once_the_field_lets_go).run()
