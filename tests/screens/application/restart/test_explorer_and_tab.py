from pathlib import Path
from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.state.current import Current
from tests.screens.application.restart.constants import RECORDINGS_FOLDER
from tests.screens.application.restart.steps import home_folder, leave, recording_in, world_with
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World, screen_filling_state
from tests.suite.screens.written import written_state

UNTOUCHED_FOLDER: Final[str] = "Untouched"


def explorer_world(opened: List[Path]) -> World:
    """A home with ``opened`` folders expanded in the session and recordings in two folders."""
    state = screen_filling_state().model_copy(update={"expanded_directories": opened})
    return world_with(state, recording_in(RECORDINGS_FOLDER), recording_in(UNTOUCHED_FOLDER))


def expect_row(screen: Screen, folder: Path) -> Item:
    """Waits for the explorer's row of ``folder`` and returns it."""
    return screen.expect_item(
        lambda: screen.explorer.file_row(folder),
        description=f"the row of {folder.name}",
    )


class TestLeavingWritesAFolderOpenedInTheExplorer:
    """A folder opened in the explorer is written as the application leaves; a sibling left closed is left
    out.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds two folders with a recording each and a session with none opened."""
        return explorer_world([])

    def test_the_session_names_the_opened_folder_alone(self, screen: Screen) -> None:
        """The session at exit names the opened folder and leaves the sibling out."""
        explorer = screen.explorer
        opened = home_folder(RECORDINGS_FOLDER)
        row = expect_row(screen, opened)
        assert not explorer.is_open(row)

        explorer.double_click(row)

        screen.expect(lambda: explorer.is_open(row), bool, description="the folder open")
        leave(screen)
        written = written_state().expanded_directories
        assert opened in written
        assert home_folder(UNTOUCHED_FOLDER) not in written


class TestAHomeHoldingAnOpenedFolderShowsIt:
    """A folder the session names as opened stands open at the start; a sibling left out stands closed."""

    @pytest.fixture
    def world(self) -> World:
        """The home holds two folders with a recording each and a session naming one as opened."""
        return explorer_world([home_folder(RECORDINGS_FOLDER)])

    def test_the_named_folder_stands_open_alone(self, screen: Screen) -> None:
        """The named folder is open and its sibling is closed."""
        explorer = screen.explorer
        opened = expect_row(screen, home_folder(RECORDINGS_FOLDER))
        closed = expect_row(screen, home_folder(UNTOUCHED_FOLDER))

        screen.expect(lambda: explorer.is_open(opened), bool, description="the named folder open")
        assert not explorer.is_open(closed)


class TestTheTabInFrontAcrossARestart:
    """The tab in front is written as the application leaves, and brought forward at the next start."""

    @pytest.fixture
    def world(self) -> World:
        """The home holds a session with the Instructions tab in front."""
        state = screen_filling_state().model_copy(update={"current": Current(tab=Tab.INSTRUCTIONS)})
        return world_with(state)

    def test_a_home_holding_it_shows_it_and_leaving_writes_the_next(self, screen: Screen) -> None:
        """The seeded tab is in front at start, and the tab brought forward is written at exit."""
        screen.expect(screen.tabs.front, Tab.INSTRUCTIONS.__eq__, description="the Instructions tab in front")

        screen.tabs.bring_to_front(Tab.SEQUENCER)

        screen.expect(screen.tabs.front, Tab.SEQUENCER.__eq__, description="the Sequencer tab in front")
        leave(screen)
        assert written_state().current.tab is Tab.SEQUENCER
