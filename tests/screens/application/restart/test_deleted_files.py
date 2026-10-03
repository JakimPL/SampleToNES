from pathlib import Path
from typing import Final

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.favorites import Favorites
from sampletones_application.config.session.state.current import Current
from sampletones_application.config.session.state.paths import LastPaths
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.application.restart.steps import home_folder, leave
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World, screen_filling_state
from tests.suite.screens.written import written_application_config, written_state

DELETED_FOLDER: Final[str] = "Deleted"
DELETED_SUBFOLDER: Final[str] = "Deeper"
DELETED_RECONSTRUCTION: Final[str] = "Deleted.stn"
DELETED_FAVORITE: Final[str] = "deleted.wav"


def deleted_folder() -> Path:
    """The folder inside the home that the session names and the home lacks."""
    return home_folder(DELETED_FOLDER) / DELETED_SUBFOLDER


def deleted_reconstruction() -> Path:
    """The reconstruction the session names and the home lacks."""
    return RECONSTRUCTIONS_DIRECTORY / DELETED_RECONSTRUCTION


def deleted_favorite() -> Path:
    """The starred file the settings name and the home lacks."""
    return home_folder(DELETED_FAVORITE)


class TestASessionNamingDeletedFiles:
    """A session naming a folder, a reconstruction and a starred file deleted since the last run.

    The application starts quietly with nothing restored, and a dialog opens in the nearest folder
    still standing. Leaving lets go of the reconstruction that failed to open and keeps the folder and
    the starred file, so a drive plugged back in is found where it was left.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds a session and settings naming a folder, a reconstruction and a starred file that are
        gone.
        """
        state = screen_filling_state().model_copy(
            update={
                "current": Current(reconstruction=deleted_reconstruction()),
                "last_paths": LastPaths(reconstruction=deleted_folder()),
            }
        )
        return World(
            state=state,
            application_config=ApplicationConfig(favorites=Favorites(paths={deleted_favorite()})),
            config=None,
            files=(),
        )

    def test_it_restores_nothing_and_asks_in_the_nearest_standing_folder(self, screen: Screen) -> None:
        """The Open dialog starts in the current folder, and no file is open."""
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
        screen.answer_next_dialog(DialogKind.OPEN, None)

        screen.reconstructions.open_from_menu()

        request = screen.expect(
            screen.dialog_requests,
            lambda requests: len(requests) == 1,
            description="the open dialog",
        )[0]
        assert request.initial_directory == Path.cwd()
        assert screen.shown_windows() == ()
        assert screen.reconstructions.open_file() == ""

    def test_the_session_left_lets_the_reconstruction_go_and_keeps_the_folder(self, screen: Screen) -> None:
        """The session written at exit holds no reconstruction and still names the deleted dialog folder."""
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")

        leave(screen)

        state = written_state()
        assert state.current.reconstruction is None
        assert state.last_paths.reconstruction == deleted_folder()

    def test_the_settings_left_still_star_the_deleted_file(self, screen: Screen) -> None:
        """The settings written at exit keep the deleted file among the starred paths."""
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")

        leave(screen)

        assert deleted_favorite() in written_application_config().favorites.paths
