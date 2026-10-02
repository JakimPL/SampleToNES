import operator
from functools import partial
from pathlib import Path
from typing import Final, List, Tuple

import pytest

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_COLLAPSE_STRIP,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER,
    TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED,
)
from sampletones_application.tags.main import TAG_MAIN_CONVERTER_PANEL, TAG_MAIN_SOURCE_PANEL
from sampletones_core.constants.enums import ChannelName
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording, WrittenBytes
from tests.suite.screens.world import HomeFile, World, lived_in_world

KICK: Final[str] = "kick.wav"
SNARE: Final[str] = "snare.wav"
TAKES: Final[str] = "Takes"
INNER: Final[str] = "Inner"
LOOPS: Final[str] = "Loops"
NOTES: Final[str] = "Notes"
TAKES_AT_THE_TOP: Final[Tuple[str, ...]] = ("one.wav", "two.wav", "three.wav")
TAKES_INSIDE: Final[Tuple[str, ...]] = ("four.wav", "five.wav")
LOOPS_HELD: Final[Tuple[str, ...]] = ("left.wav", "right.wav")
COLLIDING: Final[Tuple[str, ...]] = ("Kick Loop.wav", "kick  loop.wav", "żółw.wav")
PLAYED_SECONDS: Final[float] = 2.0
SHORT_SECONDS: Final[float] = 0.2
TONE_FREQUENCY: Final[float] = 220.0
NOTE_TEXT: Final[bytes] = b"A folder holding words, not sounds.\n"
ROUNDS: Final[int] = 20
FIRST_COUNTED_ROUND: Final[int] = 2
POINTER_REACH: Final[int] = 4

FOLDER_ROW: Final[str] = "global.stems.template.folder_row"
CONVERT_NOTHING: Final[str] = "main.converter.label.convert_button"
CONVERT_ONE: Final[str] = "main.converter.template.convert_recording"
CANCEL_RUN: Final[str] = "main.converter.label.cancel_button"
ADD_AS_STEM: Final[str] = "main.explorer.label.context_add_stem"
ADD_FOLDER: Final[str] = "main.explorer.label.context_add_folder_stems"
NOTHING_BELOW: Final[str] = "main.converter.message.scan_nothing_below"


def home(name: str) -> Path:
    """A path in the home the application was started in."""
    return Path.cwd() / name


def recording(path: Path, seconds: float) -> HomeFile:
    return Recording(destination=path, seconds=seconds, frequency=TONE_FREQUENCY)


def gathering_world() -> World:
    files: List[HomeFile] = [
        recording(home(KICK), PLAYED_SECONDS),
        recording(home(SNARE), PLAYED_SECONDS),
        *(recording(home(TAKES) / name, SHORT_SECONDS) for name in TAKES_AT_THE_TOP),
        *(recording(home(TAKES) / INNER / name, SHORT_SECONDS) for name in TAKES_INSIDE),
        *(recording(home(LOOPS) / name, SHORT_SECONDS) for name in LOOPS_HELD),
        *(recording(home(name), SHORT_SECONDS) for name in COLLIDING),
        WrittenBytes(home(NOTES) / INNER / "readme.txt", NOTE_TEXT),
    ]
    world = lived_in_world()
    return World(
        state=world.state,
        application_config=world.application_config,
        config=world.config,
        files=tuple(files),
    )


def explorer_row(screen: Screen, path: Path) -> Item:
    return screen.expect_item(lambda: screen.explorer.file_row(path), description=f"the explorer's row of {path.name}")


def gathered(screen: Screen, *paths: Path) -> None:
    """Waits until the list holds a row for each of ``paths`` and nothing else."""
    converter = screen.main.converter
    expected = sorted(converter.list.row(path) for path in paths)
    screen.expect(
        lambda: sorted(converter.list.rows()),
        expected.__eq__,
        description=f"the list holding {[path.name for path in paths]} alone",
    )


def folder_label(screen: Screen, path: Path, count: int) -> str:
    return screen.words(FOLDER_ROW).format(name=path.name, count=count)


def wait_for_the_scan_to_end(screen: Screen) -> None:
    screen.expect(lambda: not screen.main.converter.scan_shown(), bool, description="the folder read")


@pytest.fixture
def world() -> World:
    return gathering_world()


class TestNavigatingGathersNothing:
    """Opening folders in the explorer gathers nothing; a double-click on a recording gathers that one."""

    def test_the_list_stays_empty_until_a_recording_is_double_clicked(self, screen: Screen) -> None:
        converter = screen.main.converter

        def open_folders(screen: Screen) -> None:
            for folder in (home(TAKES), home(TAKES) / INNER, home(LOOPS)):
                row = explorer_row(screen, folder)

                screen.explorer.open_by_click(row)

                screen.expect(partial(screen.explorer.is_open, row), bool, description=f"{folder.name} open")

        def the_list_stays_empty(screen: Screen) -> None:
            assert converter.list.hint_shown()
            assert not converter.list.list_shown()
            assert converter.action() == screen.words(CONVERT_NOTHING)

        def a_double_click_gathers_that_recording(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home(KICK)))

            gathered(screen, home(KICK))
            assert converter.action() == screen.words(CONVERT_ONE).format(name=home(KICK).stem)
            assert not converter.list.hint_shown()

        screen.scenario(open_folders, the_list_stays_empty, a_double_click_gathers_that_recording).run()


class TestAPlainClickOnARecording:
    """A plain click plays a recording and gathers nothing; Ctrl-click and Add as stem gather it."""

    def test_it_plays_and_the_gathering_gestures_gather(self, screen: Screen) -> None:
        converter = screen.main.converter
        playback = screen.sequencer.playback

        def a_click_plays(screen: Screen) -> None:
            screen.explorer.click(explorer_row(screen, home(KICK)))

            screen.expect(playback.can_stop, bool, description="the recording playing")
            assert converter.list.hint_shown()

        def ctrl_click_gathers(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(KICK)))

            gathered(screen, home(KICK))

        def add_as_stem_gathers(screen: Screen) -> None:
            screen.explorer.right_click(explorer_row(screen, home(SNARE)))
            screen.expect(screen.context_menu.is_shown, bool, description="the recording's menu")

            screen.context_menu.choose(screen.words(ADD_AS_STEM))

            gathered(screen, home(KICK), home(SNARE))
            assert not screen.context_menu.is_shown()

        screen.scenario(a_click_plays, ctrl_click_gathers, add_as_stem_gathers).run()


class TestGatheringAFolder:
    """A folder lands as one row counting its recordings, subfolders included, and starts no run."""

    def test_ctrl_click_and_add_folder_each_give_one_counted_row(self, screen: Screen) -> None:
        converter = screen.main.converter

        def gather_a_recording_first(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home(KICK)))

            gathered(screen, home(KICK))

        def ctrl_click_a_folder(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(TAKES)))

            gathered(screen, home(KICK), home(TAKES))
            wait_for_the_scan_to_end(screen)
            count = len(TAKES_AT_THE_TOP) + len(TAKES_INSIDE)
            assert converter.list.label(home(TAKES)) == folder_label(screen, home(TAKES), count)

        def add_folder_from_its_menu(screen: Screen) -> None:
            screen.explorer.right_click(explorer_row(screen, home(LOOPS)))
            screen.expect(screen.context_menu.is_shown, bool, description="the folder's menu")

            screen.context_menu.choose(screen.words(ADD_FOLDER))

            gathered(screen, home(KICK), home(TAKES), home(LOOPS))
            wait_for_the_scan_to_end(screen)
            assert converter.list.label(home(LOOPS)) == folder_label(screen, home(LOOPS), len(LOOPS_HELD))

        def no_run_started_and_the_recording_stands_first(screen: Screen) -> None:
            assert not converter.run_shown()
            assert converter.action() != screen.words(CANCEL_RUN)
            assert converter.list.rows()[0] == converter.list.row(home(KICK))

        screen.scenario(
            gather_a_recording_first,
            ctrl_click_a_folder,
            add_folder_from_its_menu,
            no_run_started_and_the_recording_stands_first,
        ).run()


class TestGatheringAtTheEdges:
    """Gathering holds at its edges: a folder twice, a folder of no recordings, names that collide."""

    def test_a_folder_gathered_twice_stands_once(self, screen: Screen) -> None:
        for _ in range(2):
            screen.explorer.ctrl_click(explorer_row(screen, home(TAKES)))
            wait_for_the_scan_to_end(screen)

        gathered(screen, home(TAKES))

    def test_a_folder_of_no_recordings_says_so_and_gathers_nothing(self, screen: Screen) -> None:
        converter = screen.main.converter
        notice = converter.nothing_below_notice

        def ctrl_click_a_folder_of_words(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(NOTES)))

            screen.expect(notice.is_shown, bool, description="the notice")
            assert notice.words() == screen.words(NOTHING_BELOW)

        def dismiss_and_gather_a_folder_of_sounds(screen: Screen) -> None:
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice gone")

            screen.explorer.ctrl_click(explorer_row(screen, home(LOOPS)))

            gathered(screen, home(LOOPS))

        screen.scenario(ctrl_click_a_folder_of_words, dismiss_and_gather_a_folder_of_sounds).run()

    def test_names_colliding_in_case_and_spacing_stand_apart(self, screen: Screen) -> None:
        converter = screen.main.converter
        paths = [home(name) for name in COLLIDING]

        def gather_each(screen: Screen) -> None:
            for path in paths:
                screen.explorer.ctrl_click(explorer_row(screen, path))

            gathered(screen, *paths)

        def a_box_on_one_leaves_the_others(screen: Screen) -> None:
            first, *others = paths
            before = [converter.list.channel_ticked(other, ChannelName.PULSE1) for other in others]

            converter.list.tick(first, ChannelName.PULSE1)

            screen.expect(
                lambda: converter.list.channel_ticked(first, ChannelName.PULSE1),
                (not before[0]).__eq__,
                description="the box flipped on the first",
            )
            assert [converter.list.channel_ticked(other, ChannelName.PULSE1) for other in others] == before

        screen.scenario(gather_each, a_box_on_one_leaves_the_others).run()


class TestRightClickingOverAndOver:
    """Twenty right-clicks across the browser and the list each open a menu at the pointer, and build nothing lasting."""

    def test_each_menu_stands_at_the_pointer_and_the_interface_does_not_grow(self, screen: Screen) -> None:
        converter = screen.main.converter
        menu = screen.context_menu
        counts: List[int] = []

        def gather(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home(KICK)))
            gathered(screen, home(KICK))

        def right_click_over_and_over(screen: Screen) -> None:
            for round_number in range(1, ROUNDS + 1):
                in_the_list = round_number % 2 == 0
                row = converter.list.row(home(KICK)) if in_the_list else explorer_row(screen, home(SNARE))
                if in_the_list:
                    screen.hand.scroll_into_view(row)
                    screen.hand.right_click(row)
                else:
                    screen.explorer.right_click(row)
                screen.expect(menu.is_shown, bool, description=f"the menu of round {round_number}")
                pointer = screen.pointer()

                box = menu.box()
                entries = menu.entries()
                menu.dismiss()

                screen.expect(menu.is_shown, operator.not_, description=f"the menu of round {round_number} put away")
                assert (
                    box.overlap(
                        Rect(
                            x=pointer.x - POINTER_REACH,
                            y=pointer.y - POINTER_REACH,
                            width=2 * POINTER_REACH,
                            height=2 * POINTER_REACH,
                        )
                    )
                    is not None
                ), (box, pointer)
                assert entries and all(entry.enabled or entry.label for entry in entries)
                if round_number >= FIRST_COUNTED_ROUND:
                    counts.append(screen.item_count())

        def nothing_grew(screen: Screen) -> None:
            assert counts[-1] == counts[0], counts

        screen.scenario(gather, right_click_over_and_over, nothing_grew).run()


class TestACardHeaderUnderThePointer:
    """A card's header bar lights while the pointer rests on it and settles back once it leaves."""

    def test_the_bar_lights_and_settles(self, screen: Screen) -> None:
        strip = compose_tag(TAG_MAIN_CONVERTER_PANEL, SUF_COLLAPSE_STRIP)
        elsewhere = compose_tag(TAG_MAIN_SOURCE_PANEL, SUF_COLLAPSE_STRIP)

        def rest_on_the_bar(screen: Screen) -> None:
            screen.hand.hover(strip)

            screen.expect(
                lambda: screen.theme_of(strip), TAG_GLOBAL_THEME_COLLAPSE_HEADER_HOVERED.__eq__, description="lit"
            )

        def move_off(screen: Screen) -> None:
            screen.hand.scroll_into_view(elsewhere)
            screen.hand.hover(elsewhere)

            screen.expect(
                lambda: screen.theme_of(strip), TAG_GLOBAL_THEME_COLLAPSE_HEADER.__eq__, description="settled"
            )

        screen.scenario(rest_on_the_bar, move_off).run()
