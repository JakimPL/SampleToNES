import operator
from typing import Final

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.boundaries.audio import OutputDevice
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import retitle_project, save_new_project, saved_project_title

PROJECT_FILENAME: Final[str] = "Leaving.stp"
NEW_TITLE: Final[str] = "Leaving title"
SETTLING_FRAMES: Final[int] = 10


def save_a_new_project(screen: Screen) -> None:
    """Creates a project and saves it in the projects folder."""
    save_new_project(screen, PROJECTS_DIRECTORY / PROJECT_FILENAME)


def retitle_the_project(screen: Screen) -> None:
    """Retitles the open project, leaving a change to save."""
    retitle_project(screen, NEW_TITLE)


def ask_to_leave(screen: Screen) -> None:
    """Presses the Exit shortcut and waits for the unsaved project prompt."""
    screen.press_shortcut(ShortcutId.EXIT)

    screen.expect(screen.project.unsaved_prompt.is_shown, bool, description="the unsaved project prompt")


def saved_title() -> str:
    """Reads the title stored in the saved project file."""
    return saved_project_title(PROJECTS_DIRECTORY / PROJECT_FILENAME)


class TestLeavingWithAnUnsavedProject:
    """Leaving the application with changes to a saved project asks about them first.

    A new project is saved and retitled, and the Exit shortcut pressed. Save writes the new title and
    leaves. Cancel keeps the application open with the file as it was; a second Exit and a confirmation
    then leave with the file still holding the earlier title.
    """

    def test_save_writes_the_change_and_leaves(self, screen: Screen) -> None:
        """The file holds the new title once the application stops."""

        def save_and_leave(screen: Screen) -> None:
            screen.project.unsaved_prompt.save()

            assert screen.wait_for_exit()
            assert saved_title() == NEW_TITLE

        screen.scenario(
            save_a_new_project,
            retitle_the_project,
            ask_to_leave,
            save_and_leave,
        ).run()

    def test_cancel_keeps_the_application_open_and_the_change_unsaved(self, screen: Screen) -> None:
        """The application keeps running after Cancel and the file keeps its earlier title."""

        def cancel(screen: Screen) -> None:
            screen.project.unsaved_prompt.cancel()

            screen.expect(screen.project.unsaved_prompt.is_shown, operator.not_, description="the prompt gone")
            screen.frames(SETTLING_FRAMES)
            assert screen.is_running()
            assert saved_title() != NEW_TITLE

        def leave_without_saving(screen: Screen) -> None:
            ask_to_leave(screen)

            screen.project.unsaved_prompt.confirm()

            assert screen.wait_for_exit()
            assert saved_title() != NEW_TITLE

        screen.scenario(
            save_a_new_project,
            retitle_the_project,
            ask_to_leave,
            cancel,
            leave_without_saving,
        ).run()


class TestLeavingFromTheKeyboard:
    """The exit's questions answer to the keys alone, from the first press to the last.

    After the Exit shortcut brings up the question, the next-control key and the activate key choose Save,
    write the new title and leave.
    """

    def test_tab_and_enter_save_the_change_and_leave(self, screen: Screen) -> None:
        """The file holds the new title once the application stops."""

        def save_from_the_keyboard(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.DIALOG_NEXT_CONTROL)
            screen.press_shortcut(ShortcutId.DIALOG_ACTIVATE)

            assert screen.wait_for_exit()
            assert saved_title() == NEW_TITLE

        screen.scenario(
            save_a_new_project,
            retitle_the_project,
            ask_to_leave,
            save_from_the_keyboard,
        ).run()


class TestLeavingWhereNothingCanPlay:
    """A machine offering no output device opens the application and leaves it cleanly.

    The scenario waits for the Main tab and then ends the test, which closes the application.
    """

    @pytest.fixture
    def output_device(self) -> OutputDevice:
        """The machine offers no output device."""
        return OutputDevice.NONE

    @pytest.mark.xfail(
        strict=True,
        raises=ValueError,
        reason="bugs-and-todos § Bugs: leaving the application where nothing can play",
    )
    def test_the_application_leaves_without_an_error(self, screen: Screen) -> None:
        """The application starts and stops cleanly with no output device."""
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
