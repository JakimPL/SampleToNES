import operator
from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from tests.suite.screens.holds.base import Holds
from tests.suite.screens.holds.scan import ScanHold, WindingDownScanHold
from tests.suite.screens.holds.signal import ReleaseSignal
from tests.suite.screens.screen import Screen
from tests.suite.screens.seeds.recordings import Recording
from tests.suite.screens.steps.main import explorer_row, home_path
from tests.suite.screens.vocabulary.converter import FOLDER_ROW, SCAN_PROGRESS
from tests.suite.screens.worlds.home import HomeFile, World
from tests.suite.screens.worlds.recordings import lived_in_world

MANY: Final[str] = "Many"
FEW: Final[str] = "Few"
MANY_RECORDINGS: Final[int] = 130
FEW_RECORDINGS: Final[int] = 2
REPORTED_COUNT: Final[int] = 128
SECONDS: Final[float] = 0.05
FREQUENCY: Final[float] = 330.0
WIND_DOWN_RELEASE_FILE: Final[str] = "release-winding-down-scan"
RECONSTRUCT_DIRECTORY: Final[str] = "main.explorer.label.context_reconstruct_directory"


def folder_of(name: str, count: int) -> List[HomeFile]:
    """The recordings of a folder named ``name`` holding ``count`` short takes."""
    return [
        Recording(destination=home_path(name) / f"take{index:03d}.wav", seconds=SECONDS, frequency=FREQUENCY)
        for index in range(count)
    ]


@pytest.fixture
def world() -> World:
    """A lived-in home holding a folder of many recordings and a folder of two."""
    lived_in = lived_in_world()
    return World(
        state=lived_in.state,
        application_config=None,
        config=None,
        files=(*folder_of(MANY, MANY_RECORDINGS), *folder_of(FEW, FEW_RECORDINGS)),
    )


def folder_label(screen: Screen, name: str, count: int) -> str:
    """The text of a folder's row in the list, naming the folder and its recordings."""
    return screen.words(FOLDER_ROW).format(name=name, count=count)


class TestReadingALargeFolder:
    """A folder being read shows a window naming it and counting what it found, while the rest of the
    interface answers.

    The large folder is Ctrl-clicked and a held read begins. The window reports the count so far, the
    Sequencer and Main tabs come to the front in turn, and releasing the read closes the window and
    gathers the folder as one row.
    """

    def test_the_window_counts_and_the_interface_answers_meanwhile(self, screen: Screen, scan_hold: ScanHold) -> None:
        converter = screen.main.converter

        def start_reading(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(MANY)))

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
                lambda: converter.list.has_row(home_path(MANY)),
                bool,
                description="the folder gathered",
            )
            assert converter.list.label(home_path(MANY)) == folder_label(screen, MANY, MANY_RECORDINGS)

        screen.scenario(start_reading, the_interface_answers, the_read_lands).run()


class TestStoppingARead:
    """Stop gives the read up and gathers nothing; the next Ctrl-click reads afresh.

    The large folder is read and stopped, then the small folder is Ctrl-clicked and released. The list
    ends with the small folder's row alone.
    """

    def test_stop_gathers_nothing_and_the_next_read_runs(self, screen: Screen, scan_hold: ScanHold) -> None:
        converter = screen.main.converter

        def stop_a_read(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(MANY)))
            screen.expect(converter.scan_shown, bool, description="the read under way")

            converter.stop_scan()

            screen.expect(converter.scan_shown, operator.not_, description="the window closed")

        def the_next_read_runs(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(FEW)))

            screen.expect(converter.scan_shown, bool, description="a new read under way")
            scan_hold.release()
            screen.expect(
                lambda: converter.list.has_row(home_path(FEW)), bool, description="the second folder gathered"
            )
            assert converter.list.rows() == [converter.list.row(home_path(FEW))]

        screen.scenario(stop_a_read, the_next_read_runs).run()


class TestAskingForAFolderDuringARead:
    """A folder asked for while another is being read waits; asking again once the window closes reads it.

    The large folder is read and the small folder's Reconstruct menu entry chosen meanwhile. The read
    under way goes on and the list gains only the large folder. Ctrl-clicking the small folder after
    the window closes gathers it.
    """

    def test_the_read_under_way_runs_on_and_the_folder_asked_for_reads_afterwards(
        self,
        screen: Screen,
        scan_hold: ScanHold,
    ) -> None:
        converter = screen.main.converter

        def ask_for_a_second_folder_during_a_read(screen: Screen) -> None:
            screen.explorer.ctrl_click(explorer_row(screen, home_path(MANY)))
            screen.expect(converter.scan_shown, bool, description="the read under way")

            screen.explorer.right_click(explorer_row(screen, home_path(FEW)))
            screen.expect(screen.context_menu.is_shown, bool, description="the second folder's menu")
            screen.context_menu.choose(screen.words(RECONSTRUCT_DIRECTORY))

            screen.expect(screen.context_menu.is_shown, operator.not_, description="the menu put away")
            assert converter.scan_shown()
            assert MANY in converter.scan_words()

        def the_first_read_lands(screen: Screen) -> None:
            scan_hold.release()

            screen.expect(
                lambda: converter.list.has_row(home_path(MANY)), bool, description="the first folder gathered"
            )
            assert not converter.run_shown()

        def asking_again_reads_it(screen: Screen) -> None:
            screen.expect(converter.scan_shown, operator.not_, description="the window closed")

            screen.explorer.ctrl_click(explorer_row(screen, home_path(FEW)))

            screen.expect(
                lambda: converter.list.has_row(home_path(FEW)), bool, description="the second folder gathered"
            )

        screen.scenario(
            ask_for_a_second_folder_during_a_read,
            the_first_read_lands,
            asking_again_reads_it,
        ).run()


class TestAskingForAFolderAsAStoppedReadWindsDown:
    """A folder asked for once Stop closed the window is read, as the scan promises once its window closes.

    The read of the large folder is held past its last entry, so Stop closes the window while the read still
    winds down. The small folder is Ctrl-clicked then, and the hold lets the stopped read end.
    """

    @pytest.fixture
    def scan_hold(self, screen_holds: Holds, monkeypatch: pytest.MonkeyPatch) -> WindingDownScanHold:
        """A scan hold that keeps a stopped read winding down until the scenario releases it."""
        hold = WindingDownScanHold(ReleaseSignal(Path.cwd().parent / WIND_DOWN_RELEASE_FILE))
        hold.install(monkeypatch)
        screen_holds.add(hold)
        return hold

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: a folder asked for while a stopped read winds down is dropped",
    )
    def test_the_folder_asked_for_is_read(self, screen: Screen, scan_hold: WindingDownScanHold) -> None:
        """The small folder, Ctrl-clicked just after Stop, is gathered once the hold is released."""
        converter = screen.main.converter
        screen.explorer.ctrl_click(explorer_row(screen, home_path(MANY)))
        screen.expect(converter.scan_shown, bool, description="the read under way")
        converter.stop_scan()
        screen.expect(converter.scan_shown, operator.not_, description="the window closed")

        screen.explorer.ctrl_click(explorer_row(screen, home_path(FEW)))

        scan_hold.release()
        screen.expect(lambda: converter.list.has_row(home_path(FEW)), bool, description="the folder asked for gathered")
