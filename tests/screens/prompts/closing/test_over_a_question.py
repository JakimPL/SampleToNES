import operator
from typing import Final

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.screens.prompts.closing.constants import SETTLING_FRAMES
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import convert_alone, home_path
from tests.suite.screens.steps.project import retitle_project, save_project_as, saved_project_title
from tests.suite.screens.vocabulary.dialogs import EXIT_PROJECT_MESSAGE
from tests.suite.screens.worlds.recordings import BASS, LEAD

PROJECT: Final[str] = "Closing.stp"
SAVED_TITLE: Final[str] = "Before closing"
NEW_TITLE: Final[str] = "After closing"


def change_a_saved_project(screen: Screen) -> None:
    """Saves a new titled project, then retitles it, which leaves the saved file with the first title."""
    screen.project.create()
    retitle_project(screen, SAVED_TITLE)
    save_project_as(screen, PROJECTS_DIRECTORY / PROJECT)

    retitle_project(screen, NEW_TITLE)

    assert saved_project_title(PROJECTS_DIRECTORY / PROJECT) == SAVED_TITLE


def leave_letting_the_project_go(screen: Screen) -> None:
    """Answers Exit to the question about the project and expects the saved file to keep its first title."""
    prompt = screen.project.unsaved_prompt
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()
    assert saved_project_title(PROJECTS_DIRECTORY / PROJECT) == SAVED_TITLE


class TestClosingTheWindowTwiceAtOnce:
    """Two closes before the first is answered ask about the unsaved project once.

    The saved project is retitled and the window closed twice. One question comes; Cancel keeps the
    application, and a further close asks once more and leaves on Exit.
    """

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: two closes before the first is answered ask twice",
    )
    def test_one_question_and_cancel_keeps_the_application(self, screen: Screen) -> None:
        """Two closes bring one question, and Cancel keeps the application running."""
        prompt = screen.project.unsaved_prompt

        def close_twice(screen: Screen) -> None:
            screen.close_window()
            screen.close_window()

            screen.expect(prompt.is_shown, bool, description="the question about the project")
            screen.frames(SETTLING_FRAMES)
            assert len(screen.shown_windows()) == 1

        def cancel_leaves_no_question(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.is_running()

        def close_once_more(screen: Screen) -> None:
            screen.close_window()

            leave_letting_the_project_go(screen)

        screen.scenario(change_a_saved_project, close_twice, cancel_leaves_no_question, close_once_more).run()


class TestClosingTheWindowOverTheReassignQuestion:
    """Closing the window while Keyboard settings asks to reassign keys asks about the project after the
    dialog.

    The saved project is retitled, Redo listens and Undo's keys ask to reassign. The window close waits;
    Cancel brings the dialog back, and closing the dialog brings the question about the project.
    """

    def test_the_exit_question_waits_its_turn(self, screen: Screen) -> None:
        """The question about the project comes after the reassign question and its dialog."""
        settings = screen.keyboard_settings
        reassign = settings.reassign_prompt
        prompt = screen.project.unsaved_prompt

        def ask_to_reassign(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="Keyboard settings")
            settings.listen_for(ShortcutId.REDO)

            screen.press_shortcut(ShortcutId.UNDO)

            screen.expect(reassign.is_shown, bool, description="the question about reassigning")

        def close_the_window(screen: Screen) -> None:
            screen.close_window()

            screen.frames(SETTLING_FRAMES)
            assert reassign.is_shown()
            assert not prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def answer_the_dialog_and_its_question(screen: Screen) -> None:
            reassign.cancel()
            screen.expect(settings.is_shown, bool, description="Keyboard settings back")
            screen.frames(SETTLING_FRAMES)
            assert not prompt.is_shown()

            settings.cancel()

            screen.expect(prompt.is_shown, bool, description="the question about the project")
            assert prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)
            assert len(screen.shown_windows()) == 1

        screen.scenario(
            change_a_saved_project,
            ask_to_reassign,
            close_the_window,
            answer_the_dialog_and_its_question,
            leave_letting_the_project_go,
        ).run()


class TestClosingTheWindowOverTheOverwriteQuestion:
    """Closing the window while the Converter asks to replace a run's files asks about the project after it.

    The saved project is retitled and a run is converted again, which asks about replacing. The window
    close waits; Cancel brings the question about the project.
    """

    def test_the_exit_question_waits_its_turn(self, screen: Screen) -> None:
        """The question about the project comes after the overwrite question."""
        converter = screen.main.converter
        overwrite = converter.overwrite_prompt
        prompt = screen.project.unsaved_prompt

        def convert_and_ask_to_convert_again(screen: Screen) -> None:
            convert_alone(screen, home_path(BASS), channel=ChannelName.PULSE1, replacing=[home_path(LEAD)])
            converter.end_prompt.cancel()
            screen.expect(converter.end_prompt.is_shown, operator.not_, description="the run's end answered")

            converter.press_action()

            screen.expect(overwrite.is_shown, bool, description="the question about replacing")

        def close_the_window(screen: Screen) -> None:
            screen.close_window()

            screen.frames(SETTLING_FRAMES)
            assert overwrite.is_shown()
            assert not prompt.is_shown()

        def cancel_hands_the_screen_over(screen: Screen) -> None:
            overwrite.cancel()

            screen.expect(prompt.is_shown, bool, description="the question about the project")
            assert not converter.run_shown()
            assert len(screen.shown_windows()) == 1

        screen.scenario(
            change_a_saved_project,
            convert_and_ask_to_convert_again,
            close_the_window,
            cancel_hands_the_screen_over,
            leave_letting_the_project_go,
        ).run()
