import operator
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from tests.suite.screens.dearpygui.items import Item
from tests.suite.screens.holds import Holds, ReleaseSignal, ScanHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds import Recording
from tests.suite.screens.vocabulary.converter import FOLDER_ROW, SCAN_PROGRESS
from tests.suite.screens.world import HomeFile, World, lived_in_world

MANY: Final[str] = "Many"
FEW: Final[str] = "Few"
MANY_RECORDINGS: Final[int] = 130
FEW_RECORDINGS: Final[int] = 2
REPORTED_COUNT: Final[int] = 128
SECONDS: Final[float] = 0.05
FREQUENCY: Final[float] = 330.0
SLOW_ENTRY_SECONDS: Final[float] = 2.0
SLOW_RELEASE_FILE: Final[str] = "release-slow-scan"

RECONSTRUCT_DIRECTORY: Final[str] = "main.explorer.label.context_reconstruct_directory"


def home(name: str) -> Path:
    return Path.cwd() / name


def folder_of(name: str, count: int) -> List[HomeFile]:
    return [
        Recording(destination=home(name) / f"take{index:03d}.wav", seconds=SECONDS, frequency=FREQUENCY)
        for index in range(count)
    ]


@pytest.fixture
def world() -> World:
    lived_in = lived_in_world()
    return World(
        state=lived_in.state,
        application_config=None,
        config=None,
        files=(*folder_of(MANY, MANY_RECORDINGS), *folder_of(FEW, FEW_RECORDINGS)),
    )


def explorer_row(screen: Screen, path: Path) -> Item:
    return screen.expect_item(lambda: screen.explorer.file_row(path), description=f"the explorer's row of {path.name}")


def folder_label(screen: Screen, name: str, count: int) -> str:
    return screen.words(FOLDER_ROW).format(name=name, count=count)


class TestReadingALargeFolder:
    """A folder being read shows a window naming it and counting what it found, while the rest answers."""

    def test_the_window_counts_and_the_interface_answers_meanwhile(self, screen: Screen, scan_hold: ScanHold) -> None:
        converter = screen.main.converter

        def start_reading(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(MANY)))

            expected = screen.words(SCAN_PROGRESS).format(count=REPORTED_COUNT, name=MANY)
            screen.expect(converter.scan_words, expected.__eq__, description="the count of the folder read so far")
            assert converter.scan_shown()

        def the_interface_answers(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer in front")
            screen.tabs.bring_to_front(Tab.MAIN)
            screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab back")
            assert converter.scan_shown()
            assert converter.list.hint_shown()

        def the_read_lands(screen: Screen) -> None:
            scan_hold.release()

            screen.expect(converter.scan_shown, operator.not_, description="the window closed")
            screen.expect(
                lambda: converter.list.has_row(home(MANY)),
                bool,
                description="the folder gathered",
            )
            assert converter.list.label(home(MANY)) == folder_label(screen, MANY, MANY_RECORDINGS)

        screen.scenario(start_reading, the_interface_answers, the_read_lands).run()


class TestStoppingARead:
    """Stop gives the read up and gathers nothing; the next Ctrl-click reads afresh."""

    def test_stop_gathers_nothing_and_the_next_read_runs(self, screen: Screen, scan_hold: ScanHold) -> None:
        converter = screen.main.converter

        def stop_a_read(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(MANY)))
            screen.expect(converter.scan_shown, bool, description="the read under way")

            converter.stop_scan()

            screen.expect(converter.scan_shown, operator.not_, description="the window closed")

        def the_next_read_runs(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(FEW)))

            screen.expect(converter.scan_shown, bool, description="a new read under way")
            scan_hold.release()
            screen.expect(lambda: converter.list.has_row(home(FEW)), bool, description="the second folder gathered")
            assert converter.list.rows() == [converter.list.row(home(FEW))]

        screen.scenario(stop_a_read, the_next_read_runs).run()


class TestAskingForAFolderDuringARead:
    """A folder asked for while another is being read is turned away, and asking again once the window closes reads it."""

    def test_the_read_under_way_runs_on_and_the_folder_asked_for_reads_afterwards(
        self,
        screen: Screen,
        scan_hold: ScanHold,
    ) -> None:
        converter = screen.main.converter

        def ask_for_a_second_folder_during_a_read(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home(MANY)))
            screen.expect(converter.scan_shown, bool, description="the read under way")

            screen.explorer.right_click(explorer_row(screen, home(FEW)))
            screen.expect(screen.context_menu.is_shown, bool, description="the second folder's menu")
            screen.context_menu.choose(screen.words(RECONSTRUCT_DIRECTORY))

            screen.expect(screen.context_menu.is_shown, operator.not_, description="the menu put away")
            assert converter.scan_shown()
            assert MANY in converter.scan_words()

        def the_first_read_lands(screen: Screen) -> None:
            scan_hold.release()

            screen.expect(lambda: converter.list.has_row(home(MANY)), bool, description="the first folder gathered")
            assert not converter.run_shown()

        def asking_again_reads_it(screen: Screen) -> None:
            screen.expect(converter.scan_shown, operator.not_, description="the window closed")

            screen.explorer.ctrl_click(explorer_row(screen, home(FEW)))

            screen.expect(lambda: converter.list.has_row(home(FEW)), bool, description="the second folder gathered")

        screen.scenario(
            ask_for_a_second_folder_during_a_read,
            the_first_read_lands,
            asking_again_reads_it,
        ).run()


class TestAskingForAFolderAsAStoppedReadWindsDown:
    """A folder asked for once Stop closed the window is read, as the scan promises once its window closes."""

    @pytest.fixture
    def scan_hold(self, screen_holds: Holds, monkeypatch: pytest.MonkeyPatch) -> ScanHold:
        hold = ScanHold(ReleaseSignal(Path.cwd().parent / SLOW_RELEASE_FILE), interval=SLOW_ENTRY_SECONDS)
        hold.install(monkeypatch)
        screen_holds.add(hold)
        return hold

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a folder asked for while a stopped read winds down is dropped",
    )
    def test_the_folder_asked_for_is_read(self, screen: Screen, scan_hold: ScanHold) -> None:
        converter = screen.main.converter
        screen.explorer.ctrl_click(explorer_row(screen, home(MANY)))
        screen.expect(converter.scan_shown, bool, description="the read under way")
        converter.stop_scan()
        screen.expect(converter.scan_shown, operator.not_, description="the window closed")

        screen.explorer.ctrl_click(explorer_row(screen, home(FEW)))

        scan_hold.release()
        screen.expect(lambda: converter.list.has_row(home(FEW)), bool, description="the folder asked for gathered")
