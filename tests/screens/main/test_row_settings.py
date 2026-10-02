import operator
from functools import partial
from pathlib import Path
from typing import Dict, Final, List, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_INPUT_SEARCH
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL, TAG_MAIN_EXPLORER_PANEL
from sampletones_application.ui.themes.channels import PARTIAL_CHANNEL_THEME_TAGS
from sampletones_application.utils.gui.shortcuts.ids import CHANNEL_SHORTCUT_IDS, ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.items import read_item
from tests.suite.screens.holds import ConversionHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.steps.main import choose_from_the_row_menu, gather, home_path
from tests.suite.screens.world import HomeFile, World, converting_world, lived_in_world

KICK: Final[str] = "kick.wav"
SNARE: Final[str] = "snare.wav"
PAIR: Final[str] = "Pair"
PAIR_TAKES: Final[Tuple[str, ...]] = ("left.wav", "right.wav")
PLAYED_SECONDS: Final[float] = 2.0
FREQUENCY: Final[float] = 220.0
FILTER_TEXT: Final[str] = "zz"
HELD_TIMEOUT_SECONDS: Final[float] = 60.0

NEW_RECORDINGS: Final[str] = "main.source.label.new_recordings"
FOLDER_ROW: Final[str] = "global.stems.template.folder_row"
REMOVE_RECORDING: Final[str] = "main.converter.label.context_remove_stem"
CANCEL_RUN: Final[str] = "main.converter.label.cancel_button"
PROGRESS: Final[str] = "main.converter.template.progress_template"


def recordings() -> Tuple[HomeFile, ...]:
    return (
        Recording(destination=home_path(KICK), seconds=PLAYED_SECONDS, frequency=FREQUENCY),
        Recording(destination=home_path(SNARE), seconds=PLAYED_SECONDS, frequency=FREQUENCY),
        *(
            Recording(destination=home_path(PAIR) / name, seconds=PLAYED_SECONDS, frequency=FREQUENCY)
            for name in PAIR_TAKES
        ),
    )


@pytest.fixture
def world() -> World:
    return World(state=lived_in_world().state, application_config=None, config=None, files=recordings())


def ticked(screen: Screen, path: Path) -> Dict[ChannelName, bool]:
    return {channel: screen.main.converter.list.channel_ticked(path, channel) for channel in ChannelName}


class TestTheCardFollowsThePick:
    """Source settings names the row picked, recording or folder, and reads New recordings while none is."""

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


class TestAFoldersBoxes:
    """A folder's box reads partial where its recordings disagree; one click settles them all and the next lets go."""

    def test_a_box_inside_turns_the_folders_partial_and_the_folders_settles_them(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        folder = home_path(PAIR)
        first, second = (folder / name for name in PAIR_TAKES)
        channel = ChannelName.PULSE1

        def open_the_folder(screen: Screen) -> None:
            gather(screen, folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")
            assert listing.channel_ticked(first, channel) and listing.channel_ticked(second, channel)

        def a_box_inside_changes_that_row_alone(screen: Screen) -> None:
            listing.tick(first, channel)

            screen.expect(partial(listing.channel_ticked, first, channel), operator.not_, description="the box let go")
            assert listing.channel_ticked(second, channel)
            screen.expect(
                partial(listing.channel_theme, folder, channel),
                PARTIAL_CHANNEL_THEME_TAGS[channel].__eq__,
                description="the folder's box partial",
            )
            assert not listing.channel_ticked(folder, channel)

        def the_folders_box_settles_them_all(screen: Screen) -> None:
            listing.tick(folder, channel)

            screen.expect(partial(listing.channel_ticked, folder, channel), bool, description="the folder's box held")
            assert listing.channel_ticked(first, channel) and listing.channel_ticked(second, channel)

        def the_next_click_lets_them_go(screen: Screen) -> None:
            listing.tick(folder, channel)

            screen.expect(partial(listing.channel_ticked, folder, channel), operator.not_, description="let go")
            assert not listing.channel_ticked(first, channel) and not listing.channel_ticked(second, channel)

        screen.scenario(
            open_the_folder,
            a_box_inside_changes_that_row_alone,
            the_folders_box_settles_them_all,
            the_next_click_lets_them_go,
        ).run()


class TestTheCardFollowsABoxClicked:
    """Ticking a box inside an open folder brings the card to that row, and the folder's own box to the folder."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a box clicked in the list leaves Source settings where it stood",
    )
    def test_the_card_names_the_row_whose_box_was_clicked(self, screen: Screen) -> None:
        main = screen.main
        listing = main.converter.list
        folder = home_path(PAIR)
        first = folder / PAIR_TAKES[0]
        gather(screen, folder)
        listing.toggle_folder(folder)
        screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

        listing.tick(first, ChannelName.PULSE1)

        screen.expect(main.source.subject, first.stem.__eq__, description="the card on the row clicked")
        listing.tick(folder, ChannelName.PULSE1)
        expected = screen.words(FOLDER_ROW).format(name=PAIR, count=len(PAIR_TAKES))
        screen.expect(main.source.subject, expected.__eq__, description="the card on the folder")


class TestAChannelKey:
    """A channel's key settles that channel on the row picked and no other; with nothing picked it changes nothing."""

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


class TestThePickHoldsThrough:
    """The pick stands through a second click, a double-click that plays the row, and Esc stopping it."""

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
            screen.hand.double_click(listing.row(home_path(KICK)))

            screen.expect(playback.can_stop, bool, description="the recording playing")
            assert listing.is_picked(home_path(KICK))

        def esc_stops_and_keeps_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)

            screen.expect(playback.can_stop, operator.not_, description="playback stopped")
            assert listing.is_picked(home_path(KICK))
            assert main.source.subject() == home_path(KICK).stem

        screen.scenario(pick_twice, a_double_click_plays_and_keeps_it, esc_stops_and_keeps_it).run()


class TestTheKeysOfTheList:
    """Del and the channel keys reach the picked row only while the Converter card is open and no field holds the keys."""

    def test_a_collapsed_card_keeps_del_from_the_list(self, screen: Screen) -> None:
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


class TestARightClickMovesThePick:
    """A right-click on a row not picked picks it, and Del then removes that row."""

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


class TestTheListDuringARun:
    """While a run converts the list, Del, the menu's Remove and the channel keys leave it alone."""

    @pytest.fixture
    def world(self) -> World:
        return converting_world(recordings())

    def test_the_list_stands_as_it_was_through_the_run(self, screen: Screen, conversion_hold: ConversionHold) -> None:
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


HUNDREDS: Final[str] = "Hundreds"
HUNDREDS_COUNT: Final[int] = 300
TINY_SECONDS: Final[float] = 0.01


class TestHundredsGathered:
    """Some three hundred recordings gathered: the card collapses and expands, the interface answers meanwhile, and the list scrolls end to end."""

    @pytest.fixture
    def world(self) -> World:
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
