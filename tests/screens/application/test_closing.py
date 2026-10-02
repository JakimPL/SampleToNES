import operator
from typing import Final

from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import retitle_project, save_project_as, saved_project_title

PROJECT_FILENAME: Final[str] = "Closing.stp"
SAVED_TITLE: Final[str] = "Before closing"
NEW_TITLE: Final[str] = "Closing title"


def save_a_titled_project(screen: Screen) -> None:
    screen.project.create()
    retitle_project(screen, SAVED_TITLE)
    save_project_as(screen, PROJECTS_DIRECTORY / PROJECT_FILENAME)


def change_the_title(screen: Screen) -> None:
    retitle_project(screen, NEW_TITLE)


def close_asks_first(screen: Screen) -> None:
    screen.close_window()

    screen.expect(screen.project.unsaved_prompt.is_shown, bool, description="the unsaved project prompt")


def saved_title() -> str:
    return saved_project_title(PROJECTS_DIRECTORY / PROJECT_FILENAME)


class TestClosingTheWindow:
    """The close button on the window's title bar leaves the application the way Exit does."""

    def test_an_application_with_nothing_unsaved_leaves_at_once(self, screen: Screen) -> None:
        screen.close_window()

        assert screen.wait_for_exit()


class TestClosingTheWindowOverAnUnsavedProject:
    """Closing the window with an unsaved project asks about it first, and asks again at each close."""

    def test_save_writes_the_change_and_leaves(self, screen: Screen) -> None:
        def save_and_leave(screen: Screen) -> None:
            screen.project.unsaved_prompt.save()

            assert screen.wait_for_exit()
            assert saved_title() == NEW_TITLE

        screen.scenario(
            save_a_titled_project,
            change_the_title,
            close_asks_first,
            save_and_leave,
        ).run()

    def test_cancel_keeps_the_application_and_the_file_and_the_next_close_asks_again(self, screen: Screen) -> None:
        prompt = screen.project.unsaved_prompt

        def cancel(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the prompt gone")

        def close_again(screen: Screen) -> None:
            screen.close_window()

            screen.expect(prompt.is_shown, bool, description="the unsaved project prompt again")
            assert len(prompt.shown_windows()) == 1
            assert screen.is_running()
            assert saved_title() == SAVED_TITLE

        def discard_and_leave(screen: Screen) -> None:
            prompt.confirm()

            assert screen.wait_for_exit()
            assert saved_title() == SAVED_TITLE

        screen.scenario(
            save_a_titled_project,
            change_the_title,
            close_asks_first,
            cancel,
            close_again,
            discard_and_leave,
        ).run()
