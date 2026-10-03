import operator
from functools import partial
from pathlib import Path
from typing import Dict, Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.paths import LAYOUT_DIRECTORY
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_TEXT,
    TAG_GLOBAL_THEME_STEMS_GROUP_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW,
    TAG_GLOBAL_THEME_STEMS_ROW_INERT,
)
from sampletones_application.tags.main import PRE_MAIN_CONVERTER_STEMS
from sampletones_application.ui.themes.channels import CHANNEL_THEME_TAGS
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.utils.serialization import load_yaml_model
from tests.suite.screens.dearpygui.items import Item, read_item, read_scroll
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.vocabulary.converter import CONVERT_ONE, CONVERT_SEVERAL, FOLDER_ROW, REMOVE_RECORDING
from tests.suite.screens.vocabulary.recordings import KICK, SNARE
from tests.suite.screens.world import HomeFile, World, lived_in_world

FORTY: Final[str] = "Forty"
FORTY_COUNT: Final[int] = 40
PLAYED_SECONDS: Final[float] = 2.0
SHORT_SECONDS: Final[float] = 0.02
FREQUENCY: Final[float] = 220.0
STILL_FRAMES: Final[int] = 30
SAME_LINE_PIXELS: Final[float] = 1.0
HEADING: Final[str] = "heading"

SHOW_RECORDINGS: Final[str] = "main.converter.label.context_open_folder"
HIDE_RECORDINGS: Final[str] = "main.converter.label.context_close_folder"
PLAY: Final[str] = "global.context.label.play"
CHANNEL_NAMES: Final[Dict[ChannelName, str]] = {
    ChannelName.PULSE1: "global.context.label.pulse_1",
    ChannelName.PULSE2: "global.context.label.pulse_2",
    ChannelName.TRIANGLE: "global.context.label.triangle",
    ChannelName.NOISE: "global.context.label.noise",
}


def home(name: str) -> Path:
    return Path.cwd() / name


def take(index: int) -> str:
    return f"take{index:02d}.wav"


def recording(path: Path, seconds: float) -> HomeFile:
    return Recording(destination=path, seconds=seconds, frequency=FREQUENCY)


@pytest.fixture
def world() -> World:
    files: List[HomeFile] = [
        recording(home(KICK), PLAYED_SECONDS),
        recording(home(SNARE), PLAYED_SECONDS),
        *(recording(home(FORTY) / take(index), SHORT_SECONDS) for index in range(FORTY_COUNT)),
    ]
    return World(state=lived_in_world().state, application_config=None, config=None, files=tuple(files))


def explorer_row(screen: Screen, path: Path) -> Item:
    return screen.expect_item(lambda: screen.explorer.file_row(path), description=f"the explorer's row of {path.name}")


def gather(screen: Screen, *paths: Path) -> None:
    """Ctrl-clicks each of ``paths`` in the explorer and waits for its row."""
    converter = screen.main.converter
    for path in paths:
        screen.explorer.ctrl_click(explorer_row(screen, path))
        screen.expect(partial(converter.list.has_row, path), bool, description=f"{path.name} gathered")
        screen.expect(lambda: not converter.scan_shown(), bool, description="the read done")


def choose_from_the_row_menu(screen: Screen, path: Path, entry: str) -> None:
    row = screen.main.converter.list.row(path)
    screen.hand.scroll_into_view(row)
    screen.hand.right_click(row)
    screen.expect(screen.context_menu.is_shown, bool, description=f"the menu of {path.name}")
    screen.context_menu.choose(entry)


class TestAFolderInTheList:
    """A gathered folder arrives closed; its marker, a double-click on its name and its menu each open and close it."""

    def test_each_gesture_opens_and_closes_it(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(FORTY)

        def arrives_closed(screen: Screen) -> None:
            gather(screen, folder)

            assert not listing.is_open(folder)

        def the_marker(screen: Screen) -> None:
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="open by its marker")

            listing.toggle_folder(folder)

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed by its marker")

        def a_double_click_on_its_name(screen: Screen) -> None:
            screen.hand.double_click(listing.row(folder))
            screen.expect(partial(listing.is_open, folder), bool, description="open by a double-click")

            screen.hand.double_click(listing.row(folder))

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed by a double-click")

        def its_menu(screen: Screen) -> None:
            choose_from_the_row_menu(screen, folder, screen.words(SHOW_RECORDINGS))
            screen.expect(partial(listing.is_open, folder), bool, description="open from its menu")

            choose_from_the_row_menu(screen, folder, screen.words(HIDE_RECORDINGS))

            screen.expect(partial(listing.is_open, folder), operator.not_, description="closed from its menu")

        screen.scenario(arrives_closed, the_marker, a_double_click_on_its_name, its_menu).run()


class TestAFolderThatScrolls:
    """An open folder of forty scrolls in its own region, end to end, and its rows hold still under the pointer."""

    def test_it_scrolls_on_its_own_to_its_last_row(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(FORTY)
        region = listing.tags.region(str(folder))
        last = folder / take(FORTY_COUNT - 1)

        def open_it(screen: Screen) -> None:
            gather(screen, home(KICK), folder)
            listing.toggle_folder(folder)

            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")
            assert screen.bridge.ask(lambda: read_scroll(region)).maximum > 0

        def the_wheel_takes_it_to_its_last_row(screen: Screen) -> None:
            well_before = screen.bridge.ask(lambda: read_scroll(listing.tags.well))

            screen.hand.scroll_to_end(region)

            screen.expect(partial(listing.has_row, last), bool, description="the last row drawn")
            screen.hand.scroll_into_view(listing.row(last))
            screen.hand.hover(listing.row(last))
            assert screen.bridge.ask(lambda: read_scroll(listing.tags.well)) == well_before

        def rows_hold_still_under_the_pointer(screen: Screen) -> None:
            row = listing.row(last)
            screen.hand.hover(row)

            with screen.record(lambda: read_item(row).rect) as recording:
                screen.frames(STILL_FRAMES)

            assert len(set(recording.values())) == 1, recording.values()

        screen.scenario(open_it, the_wheel_takes_it_to_its_last_row, rows_hold_still_under_the_pointer).run()


class TestTheListComingAndGoing:
    """With nothing gathered the hint stands alone; the first recording brings the list and removing the last takes it away."""

    def test_the_hint_and_the_list_take_turns(self, screen: Screen) -> None:
        listing = screen.main.converter.list

        def the_hint_alone(screen: Screen) -> None:
            assert listing.hint_shown()
            assert not listing.list_shown()

        def the_first_recording_brings_the_list(screen: Screen) -> None:
            gather(screen, home(KICK))

            assert listing.list_shown()
            assert not listing.hint_shown()

        def removing_the_last_takes_it_away(screen: Screen) -> None:
            listing.remove(home(KICK))

            screen.expect(listing.hint_shown, bool, description="the hint back")
            assert not listing.list_shown()
            assert listing.rows() == []

        screen.scenario(the_hint_alone, the_first_recording_brings_the_list, removing_the_last_takes_it_away).run()


class TestRemovingFolders:
    """Removing a recording inside an open folder or the folder itself takes what it names and nothing else."""

    def test_a_recording_inside_goes_alone_and_the_folder_counts_one_fewer(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(FORTY)
        removed = folder / take(1)

        def open_the_folder_beside_a_recording(screen: Screen) -> None:
            gather(screen, home(KICK), folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

        def remove_one_inside(screen: Screen) -> None:
            outside = screen.bridge.ask(lambda: dpg.get_alias_id(listing.row(home(KICK))))

            listing.remove(removed)

            screen.expect(partial(listing.has_row, removed), operator.not_, description="the recording gone")
            expected = screen.words(FOLDER_ROW).format(name=folder.name, count=FORTY_COUNT - 1)
            screen.expect(partial(listing.label, folder), expected.__eq__, description="the folder counting one fewer")
            assert listing.has_row(folder / take(0)) and listing.has_row(folder / take(2))
            assert listing.is_open(folder)
            assert screen.bridge.ask(lambda: dpg.get_alias_id(listing.row(home(KICK)))) == outside

        screen.scenario(open_the_folder_beside_a_recording, remove_one_inside).run()

    def test_an_open_folder_goes_with_its_recordings_and_comes_back_closed(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(FORTY)

        def remove_it_open(screen: Screen) -> None:
            gather(screen, home(KICK), folder)
            listing.toggle_folder(folder)
            screen.expect(partial(listing.is_open, folder), bool, description="the folder open")

            listing.remove(folder)

            screen.expect(partial(listing.has_row, folder), operator.not_, description="the folder gone")
            assert listing.rows() == [listing.row(home(KICK))]

        def gather_it_again(screen: Screen) -> None:
            gather(screen, folder)

            assert not listing.is_open(folder)
            assert listing.rows() == [listing.row(home(KICK)), listing.row(folder)]

        screen.scenario(remove_it_open, gather_it_again).run()


class TestUntickingEveryChannel:
    """A recording with no channel left reads as out of play and leaves the run, while it stays listed."""

    def test_the_row_dims_and_the_run_counts_without_it(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        converter = screen.main.converter

        def gather_two(screen: Screen) -> None:
            gather(screen, home(KICK), home(SNARE))

            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        def untick_every_channel_of_one(screen: Screen) -> None:
            for channel in ChannelName:
                if listing.channel_ticked(home(KICK), channel):
                    listing.tick(home(KICK), channel)
                    screen.expect(
                        partial(listing.channel_ticked, home(KICK), channel),
                        operator.not_,
                        description=f"{channel} let go",
                    )

            screen.expect(
                partial(listing.row_theme, home(KICK)),
                TAG_GLOBAL_THEME_STEMS_ROW_INERT.__eq__,
                description="the row out of play",
            )
            assert converter.action() == screen.words(CONVERT_ONE).format(name=home(SNARE).stem)
            assert listing.has_row(home(KICK))

        def one_channel_brings_it_back(screen: Screen) -> None:
            listing.tick(home(KICK), ChannelName.PULSE1)

            screen.expect(
                partial(listing.row_theme, home(KICK)),
                TAG_GLOBAL_THEME_STEMS_ROW.__eq__,
                description="the row in play",
            )
            assert converter.action() == screen.words(CONVERT_SEVERAL).format(count=2)

        screen.scenario(gather_two, untick_every_channel_of_one, one_channel_brings_it_back).run()


class TestPlayingFromTheList:
    """A recording in the list plays at a double-click, and its menu leads with Play while its file stands."""

    def test_a_double_click_plays_and_play_greys_once_the_file_is_gone(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        menu = screen.context_menu

        def a_double_click_plays(screen: Screen) -> None:
            gather(screen, home(KICK))

            screen.hand.double_click(listing.row(home(KICK)))

            screen.expect(screen.sequencer.playback.can_stop, bool, description="the recording playing")
            assert listing.rows() == [listing.row(home(KICK))]

        def its_menu_leads_with_play(screen: Screen) -> None:
            screen.hand.right_click(listing.row(home(KICK)))
            screen.expect(menu.is_shown, bool, description="the menu")

            first = menu.entries()[0]

            assert (first.label, first.enabled) == (screen.words(PLAY), True)
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")

        def play_greys_once_the_file_is_gone(screen: Screen) -> None:
            home(KICK).unlink()

            screen.hand.right_click(listing.row(home(KICK)))
            screen.expect(menu.is_shown, bool, description="the menu again")

            first = menu.entries()[0]

            assert (first.label, first.enabled) == (screen.words(PLAY), False)
            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away again")

        screen.scenario(a_double_click_plays, its_menu_leads_with_play, play_greys_once_the_file_is_gone).run()


class TestTheListsLook:
    """The channel names above the list wear their channel's colour; a folder row carries the band and matches a recording's height."""

    def test_names_bands_and_lines(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(FORTY)

        def gather_a_recording_and_a_folder(screen: Screen) -> None:
            gather(screen, home(KICK), folder)

        def the_channel_names_wear_their_colours(screen: Screen) -> None:
            for channel, key in CHANNEL_NAMES.items():
                name = compose_tag(PRE_MAIN_CONVERTER_STEMS, HEADING, channel, SUF_TEXT)

                assert screen.bridge.ask(partial(dpg.get_value, name)) == screen.words(key)
                assert screen.theme_of(name) == CHANNEL_THEME_TAGS[channel]

        def the_folder_alone_carries_the_band(screen: Screen) -> None:
            assert listing.band_theme(folder) == TAG_GLOBAL_THEME_STEMS_GROUP_ROW
            assert listing.band_theme(home(KICK)) != TAG_GLOBAL_THEME_STEMS_GROUP_ROW

        def rows_share_a_height_and_names_share_a_line_with_their_boxes(screen: Screen) -> None:
            folder_box = screen.bridge.ask(lambda: read_item(listing.row(folder)).rect)
            recording_box = screen.bridge.ask(lambda: read_item(listing.row(home(KICK))).rect)
            check_box = screen.bridge.ask(lambda: read_item(listing.channel_box(home(KICK), ChannelName.PULSE1)).rect)
            assert folder_box is not None and recording_box is not None and check_box is not None

            assert folder_box.height == recording_box.height
            assert (
                abs((recording_box.y + recording_box.height / 2) - (check_box.y + check_box.height / 2))
                <= SAME_LINE_PIXELS
            )

        screen.scenario(
            gather_a_recording_and_a_folder,
            the_channel_names_wear_their_colours,
            the_folder_alone_carries_the_band,
            rows_share_a_height_and_names_share_a_line_with_their_boxes,
        ).run()


THOUSANDS: Final[str] = "Thousands"
THOUSANDS_COUNT: Final[int] = 1500
TINY_SECONDS: Final[float] = 0.01
ONE_ROW: Final[int] = 1
STEMS_LAYOUT: Final[Path] = LAYOUT_DIRECTORY / "general" / "stems.yaml"
MENU_ROW: Final[int] = 3
WHEEL_PAST: Final[int] = 5


def thousand(index: int) -> str:
    return f"take{index:04d}.wav"


def rows_inside(screen: Screen, folder: Path) -> List[str]:
    listing = screen.main.converter.list
    inside = {listing.row(folder / thousand(index)) for index in range(THOUSANDS_COUNT)}
    return [row for row in listing.rows() if row in inside]


class TestAFolderOfThousands:
    """A folder of thousands opens drawing only the rows in view, and its last row and any menu still answer."""

    @pytest.fixture
    def world(self) -> World:
        files = [
            Recording(destination=home(THOUSANDS) / thousand(index), seconds=TINY_SECONDS, frequency=FREQUENCY)
            for index in range(THOUSANDS_COUNT)
        ]
        return World(state=lived_in_world().state, application_config=None, config=None, files=tuple(files))

    def open_it(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        gather(screen, home(THOUSANDS))
        listing.toggle_folder(home(THOUSANDS))
        screen.expect(partial(listing.is_open, home(THOUSANDS)), bool, description="the folder open")

    def test_it_draws_the_rows_in_view_and_reaches_its_last(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        folder = home(THOUSANDS)
        region = listing.tags.region(str(folder))
        last = folder / thousand(THOUSANDS_COUNT - 1)

        def opens_drawing_what_is_in_view(screen: Screen) -> None:
            self.open_it(screen)
            drawn = rows_inside(screen, folder)
            region_box = screen.bridge.ask(lambda: read_item(region).rect)
            first = screen.bridge.ask(lambda: read_item(drawn[0]).rect)
            second = screen.bridge.ask(lambda: read_item(drawn[1]).rect)
            assert region_box is not None and first is not None and second is not None
            pitch = second.y - first.y
            overscan = load_yaml_model(STEMS_LAYOUT, StemsListLayout).window_overscan

            assert len(drawn) <= int(region_box.height / pitch) + ONE_ROW + 2 * overscan

        def reaches_the_last_row(screen: Screen) -> None:
            screen.hand.scroll_to_end(region)

            screen.expect(partial(listing.has_row, last), bool, description="the last row drawn")
            screen.hand.scroll_into_view(listing.row(last))
            screen.hand.hover(listing.row(last))

        screen.scenario(opens_drawing_what_is_in_view, reaches_the_last_row).run()

    def test_remove_chosen_after_the_wheel_turned_removes_the_row_the_menu_was_opened_on(self, screen: Screen) -> None:
        listing = screen.main.converter.list
        menu = screen.context_menu
        folder = home(THOUSANDS)
        region = listing.tags.region(str(folder))
        target = folder / thousand(MENU_ROW)

        def open_the_menu_and_turn_the_wheel(screen: Screen) -> None:
            self.open_it(screen)
            screen.hand.scroll_into_view(listing.row(target))
            screen.hand.right_click(listing.row(target))
            screen.expect(menu.is_shown, bool, description="the row's menu")

            screen.hand.turn_wheel_over(region, WHEEL_PAST)

            assert menu.is_shown()

        def remove_from_the_menu(screen: Screen) -> None:
            menu.choose(screen.words(REMOVE_RECORDING))

            expected = screen.words(FOLDER_ROW).format(name=folder.name, count=THOUSANDS_COUNT - 1)
            screen.expect(partial(listing.label, folder), expected.__eq__, description="one row fewer")

        def that_row_alone_went(screen: Screen) -> None:
            screen.hand.turn_wheel_over(region, -2 * WHEEL_PAST)
            screen.expect(partial(listing.has_row, folder / thousand(0)), bool, description="the top in view")

            assert not listing.has_row(target)
            assert listing.has_row(folder / thousand(MENU_ROW - 1)) and listing.has_row(folder / thousand(MENU_ROW + 1))

        screen.scenario(open_the_menu_and_turn_the_wheel, remove_from_the_menu, that_row_alone_went).run()
