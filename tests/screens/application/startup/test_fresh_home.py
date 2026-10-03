from pathlib import Path

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.paths.user import LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World
from tests.suite.screens.written import written_application_config, written_config, written_state


class TestAFreshHome:
    """The application starts in a home no run has used, and leaves behind what the next start reads.

    The application opens on the folder it was started in with the Main tab in front and no window shown,
    and lists the library and reconstructions folders. Exit then writes the Main tab as the session's tab,
    the library folder in the settings, and the application's version.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds no session, no settings and no files."""
        return World(
            state=None,
            application_config=None,
            config=None,
            files=(),
        )

    def test_it_opens_on_the_folder_it_was_started_in_and_leaves_its_settings(self, screen: Screen) -> None:
        """The first start opens on its folder, and Exit writes the session and both settings files."""
        explorer = screen.explorer

        def opens_on_its_folder(screen: Screen) -> None:
            screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")

            home = screen.expect_item(
                lambda: explorer.file_row(Path.cwd()),
                description="the folder the application was started in",
            )

            assert explorer.is_open(home)
            assert screen.shown_windows() == ()

        def lists_the_folders_it_keeps_its_documents_in(screen: Screen) -> None:
            for folder in (LIBRARY_DIRECTORY, RECONSTRUCTIONS_DIRECTORY):
                assert explorer.file_row(folder) is not None, folder

        def leaves_its_settings_behind(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()
            assert written_state().current.tab is Tab.MAIN
            assert Path(written_config().general.library_directory) == LIBRARY_DIRECTORY
            assert written_application_config().metadata.version is not None

        screen.scenario(
            opens_on_its_folder,
            lists_the_folders_it_keeps_its_documents_in,
            leaves_its_settings_behind,
        ).run()
