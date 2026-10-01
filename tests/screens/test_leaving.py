import operator
from typing import Final

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.project import ProjectContainer
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.boundaries.audio import OutputDevice
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen

PROJECT_FILENAME: Final[str] = "Leaving.stp"
NEW_TITLE: Final[str] = "Leaving title"
SETTLING_FRAMES: Final[int] = 10


def save_a_new_project(screen: Screen) -> None:
    project = screen.project
    project.create()
    screen.answer_next_dialog(DialogKind.SAVE, PROJECTS_DIRECTORY / PROJECT_FILENAME)

    project.save_as()

    screen.expect(project.saved_notice.is_shown, bool, description="the project saved notice")
    project.saved_notice.confirm()
    screen.expect(project.saved_notice.is_shown, operator.not_, description="the notice gone")


def retitle_the_project(screen: Screen) -> None:
    properties = screen.project.properties
    properties.open()
    screen.expect(properties.is_shown, bool, description="the Project properties dialog")

    properties.retitle(NEW_TITLE)
    properties.confirm()

    screen.expect(properties.is_shown, operator.not_, description="the dialog closed")


def ask_to_leave(screen: Screen) -> None:
    screen.press_shortcut(ShortcutId.EXIT)

    screen.expect(screen.project.unsaved_prompt.is_shown, bool, description="the unsaved project prompt")


def saved_title() -> str:
    return ProjectContainer.load(PROJECTS_DIRECTORY / PROJECT_FILENAME).info.title


class TestLeavingWithAnUnsavedProject:
    """Leaving the application with changes to a saved project asks about them first."""

    def test_save_writes_the_change_and_leaves(self, screen: Screen) -> None:
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
    """The exit's questions answer to the keys alone, from the first press to the last."""

    def test_tab_and_enter_save_the_change_and_leave(self, screen: Screen) -> None:
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
    """A machine offering no output device opens the application and leaves it cleanly."""

    @pytest.fixture
    def output_device(self) -> OutputDevice:
        return OutputDevice.NONE

    @pytest.mark.xfail(
        strict=True,
        raises=ValueError,
        reason="bugs-and-todos § Bugs: leaving the application where nothing can play",
    )
    def test_the_application_leaves_without_an_error(self, screen: Screen) -> None:
        screen.expect(screen.tabs.front, Tab.MAIN.__eq__, description="the Main tab in front")
