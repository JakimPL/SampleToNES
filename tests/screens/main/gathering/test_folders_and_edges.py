import operator
from pathlib import Path
from typing import Final

from sampletones_core.constants.enums import ChannelName
from tests.screens.main.gathering.constants import (
    COLLIDING,
    LOOPS,
    LOOPS_HELD,
    NOTES,
    TAKES,
    TAKES_AT_THE_TOP,
    TAKES_INSIDE,
)
from tests.screens.main.gathering.steps import gathered
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import explorer_row, home_path
from tests.suite.screens.vocabulary.converter import CANCEL_RUN, FOLDER_ROW
from tests.suite.screens.vocabulary.recordings import KICK

ADD_FOLDER: Final[str] = "main.explorer.label.context_add_folder_stems"
NOTHING_BELOW: Final[str] = "main.converter.message.scan_nothing_below"


def folder_label(screen: Screen, path: Path, count: int) -> str:
    """Returns the text a folder row shows for ``path`` holding ``count`` recordings."""
    return screen.words(FOLDER_ROW).format(name=path.name, count=count)


def wait_for_the_scan_to_end(screen: Screen) -> None:
    """Waits until the Converter has finished reading the folders it was given."""
    screen.expect(lambda: not screen.main.converter.scan_shown(), bool, description="the folder read")


class TestGatheringAFolder:
    """A folder lands as one row counting its recordings, subfolders included, and starts no run.

    A recording is gathered first. Ctrl-click on the Takes folder and Add folder from the menu of the
    Loops folder each add one counted row. The scenario ends with no run on screen and the recording
    still on top.
    """

    def test_ctrl_click_and_add_folder_each_give_one_counted_row(self, screen: Screen) -> None:
        """Each gesture gives its folder one row with the count of the recordings inside."""
        converter = screen.main.converter

        def gather_a_recording_first(screen: Screen) -> None:
            screen.explorer.double_click(explorer_row(screen, home_path(KICK)))

            gathered(screen, home_path(KICK))

        def ctrl_click_a_folder(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(TAKES)))

            gathered(screen, home_path(KICK), home_path(TAKES))
            wait_for_the_scan_to_end(screen)
            count = len(TAKES_AT_THE_TOP) + len(TAKES_INSIDE)
            assert converter.list.label(home_path(TAKES)) == folder_label(screen, home_path(TAKES), count)

        def add_folder_from_its_menu(screen: Screen) -> None:
            screen.explorer.right_click(explorer_row(screen, home_path(LOOPS)))
            screen.expect(screen.context_menu.is_shown, bool, description="the folder's menu")

            screen.context_menu.choose(screen.words(ADD_FOLDER))

            gathered(screen, home_path(KICK), home_path(TAKES), home_path(LOOPS))
            wait_for_the_scan_to_end(screen)
            assert converter.list.label(home_path(LOOPS)) == folder_label(screen, home_path(LOOPS), len(LOOPS_HELD))

        def no_run_started_and_the_recording_stands_first(screen: Screen) -> None:
            assert not converter.run_shown()
            assert converter.action() != screen.words(CANCEL_RUN)
            assert converter.list.rows()[0] == converter.list.row(home_path(KICK))

        screen.scenario(
            gather_a_recording_first,
            ctrl_click_a_folder,
            add_folder_from_its_menu,
            no_run_started_and_the_recording_stands_first,
        ).run()


class TestGatheringAtTheEdges:
    """Gathering copes with its edges: a folder gathered twice, a folder with no recordings and names that
    collide.
    """

    def test_a_folder_gathered_twice_stands_once(self, screen: Screen) -> None:
        """Ctrl-clicking the same folder twice leaves one row for it."""
        for _ in range(2):
            screen.explorer.ctrl_click(explorer_row(screen, home_path(TAKES)))
            wait_for_the_scan_to_end(screen)

        gathered(screen, home_path(TAKES))

    def test_a_folder_of_no_recordings_says_so_and_gathers_nothing(self, screen: Screen) -> None:
        """A folder holding only words shows a notice and adds no row; the next folder of sounds gathers
        once the notice is dismissed.
        """
        converter = screen.main.converter
        notice = converter.nothing_below_notice

        def ctrl_click_a_folder_of_words(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(NOTES)))

            screen.expect(notice.is_shown, bool, description="the notice")
            assert notice.words() == screen.words(NOTHING_BELOW)

        def dismiss_and_gather_a_folder_of_sounds(screen: Screen) -> None:
            notice.dismiss()
            screen.expect(notice.is_shown, operator.not_, description="the notice gone")

            screen.explorer.ctrl_click(explorer_row(screen, home_path(LOOPS)))

            gathered(screen, home_path(LOOPS))

        screen.scenario(ctrl_click_a_folder_of_words, dismiss_and_gather_a_folder_of_sounds).run()

    def test_names_colliding_in_case_and_spacing_stand_apart(self, screen: Screen) -> None:
        """Recordings whose names differ only in case or spacing get separate rows, and ticking a box on
        one leaves the others as they were.
        """
        converter = screen.main.converter
        paths = [home_path(name) for name in COLLIDING]

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
