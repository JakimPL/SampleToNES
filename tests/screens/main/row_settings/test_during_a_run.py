import operator
from functools import partial
from typing import Dict, Final, List

import pytest

from sampletones_application.utils.gui.shortcuts.ids import CHANNEL_SHORTCUT_IDS, ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.main.row_settings.steps import recordings, ticked
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.holds.conversion import ConversionHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import choose_from_the_row_menu, gather, home_path
from tests.suite.screens.vocabulary.converter import CANCEL_RUN, REMOVE_RECORDING
from tests.suite.screens.vocabulary.recordings import KICK, SNARE
from tests.suite.screens.worlds.home import World
from tests.suite.screens.worlds.recordings import converting_world

HELD_TIMEOUT_SECONDS: Final[float] = 60.0
PROGRESS: Final[str] = "main.converter.template.progress_template"


class TestTheListDuringARun:
    """While a run converts the list, Del, the menu's Remove and the channel keys leave the list as it is;
    after the run they reach the rows again.

    A kick and a snare recording are gathered and a held run starts. Del and the Pulse 2 key then act on
    the picked kick, whose row is disabled and whose boxes stay as they were. Once the run ends and its
    question is closed, the menu's Remove takes the snare away and Del takes the kick away.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home holding the recordings, set up to convert them."""
        return converting_world(recordings())

    def test_the_list_stands_as_it_was_through_the_run(self, screen: Screen, conversion_hold: ConversionHold) -> None:
        """The rows and their boxes stay the same through the run, and removal works again after it."""
        converter = screen.main.converter
        listing = converter.list
        before: List[Dict[ChannelName, bool]] = []

        def start_a_held_run(screen: Screen) -> None:
            gather(screen, home_path(KICK), home_path(SNARE))
            listing.pick(home_path(KICK))
            before.append(ticked(screen, home_path(KICK)))

            converter.press_action()

            started = screen.words(PROGRESS).format(0, 2)
            screen.bridge.expect(
                converter.status,
                lambda status: status.startswith(started),
                description="the run under way on its first recording",
                timeout=HELD_TIMEOUT_SECONDS,
            )
            assert converter.action() == screen.words(CANCEL_RUN)

        def the_keys_and_the_menu_reach_nothing(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)
            screen.press_shortcut(CHANNEL_SHORTCUT_IDS[ChannelName.PULSE2])

            assert not screen.bridge.ask(lambda: read_item(listing.row(home_path(KICK)))).enabled
            assert not screen.context_menu.is_shown()
            assert listing.rows() == [listing.row(home_path(KICK)), listing.row(home_path(SNARE))]
            assert ticked(screen, home_path(KICK)) == before[0]

        def after_the_run_the_menu_and_del_reach_the_row(screen: Screen) -> None:
            conversion_hold.release()
            screen.bridge.expect(
                converter.end_prompt.is_shown,
                bool,
                description="the run's end",
                timeout=HELD_TIMEOUT_SECONDS,
            )
            converter.end_prompt.cancel()
            screen.expect(converter.end_prompt.is_shown, operator.not_, description="the end prompt closed")
            assert ticked(screen, home_path(KICK)) == before[0]

            choose_from_the_row_menu(screen, home_path(SNARE), screen.words(REMOVE_RECORDING))
            screen.expect(
                partial(listing.has_row, home_path(SNARE)), operator.not_, description="removed from the menu"
            )
            listing.pick(home_path(KICK))
            screen.press_shortcut(ShortcutId.SOURCES_REMOVE_SOURCE)

            screen.expect(partial(listing.has_row, home_path(KICK)), operator.not_, description="removed by Del")

        screen.scenario(
            start_a_held_run,
            the_keys_and_the_menu_reach_nothing,
            after_the_run_the_menu_and_del_reach_the_row,
        ).run()
