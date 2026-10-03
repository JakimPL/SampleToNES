import operator
from typing import Final, List

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_shared.paths.user import PROJECTS_DIRECTORY
from tests.suite.screens.application import Startup
from tests.suite.screens.holds import RegenerationHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import convert_alone, home_path
from tests.suite.screens.steps.project import retitle_project, save_project_as, saved_project_title
from tests.suite.screens.steps.reconstructions import (
    expect_open,
    first_raised,
    marked,
    raise_the_first_level_while_held,
    titled,
)
from tests.suite.screens.vocabulary.dialogs import EXIT_PROJECT_MESSAGE
from tests.suite.screens.world import BASS, LEAD, OPEN_RECONSTRUCTION

SETTLING_FRAMES: Final[int] = 30
PROJECT: Final[str] = "Closing.stp"
SAVED_TITLE: Final[str] = "Before closing"
NEW_TITLE: Final[str] = "After closing"


def change_a_saved_project(screen: Screen) -> None:
    """Saves a new project titled, then titles it anew, which leaves it unsaved."""
    screen.project.create()
    retitle_project(screen, SAVED_TITLE)
    save_project_as(screen, PROJECTS_DIRECTORY / PROJECT)

    retitle_project(screen, NEW_TITLE)

    assert saved_project_title(PROJECTS_DIRECTORY / PROJECT) == SAVED_TITLE


def leave_letting_the_project_go(screen: Screen) -> None:
    prompt = screen.project.unsaved_prompt
    screen.expect(prompt.is_shown, bool, description="the question about the project")

    prompt.confirm()

    assert screen.wait_for_exit()
    assert saved_project_title(PROJECTS_DIRECTORY / PROJECT) == SAVED_TITLE


class TestClosingTheWindowTwiceAtOnce:
    """Two closes before the first is answered ask about the unsaved project once."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: two closes before the first is answered ask twice",
    )
    def test_one_question_and_cancel_keeps_the_application(self, screen: Screen) -> None:
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
    """Closing the window while Keyboard settings asks to reassign keys asks about the project after the dialog."""

    def test_the_exit_question_waits_its_turn(self, screen: Screen) -> None:
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
    """Closing the window while the Converter asks to replace a run's files asks about the project after it."""

    def test_the_exit_question_waits_its_turn(self, screen: Screen) -> None:
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


class TestClosingTheWindowWhileAnEditIsOnItsWay:
    """A close asked for while an edit is on its way asks about the edited reconstruction once the edit lands."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: two closes before the first is answered ask twice",
    )
    def test_two_closes_ask_once(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt

        def edit_and_close_twice_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)

            screen.close_window()
            screen.close_window()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        def the_edit_lands_and_one_question_comes(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the question about leaving")
            screen.frames(SETTLING_FRAMES)
            assert len(screen.shown_windows()) == 1

        def cancel_leaves_no_question(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        screen.scenario(
            edit_and_close_twice_while_the_rebuild_is_held,
            the_edit_lands_and_one_question_comes,
            cancel_leaves_no_question,
        ).run()

    def test_an_edit_made_after_the_close_is_drawn_away(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        typed: List[str] = []

        def edit_and_close_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            typed.append(raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1))

            screen.close_window()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        def edit_again_after_the_close(screen: Screen) -> None:
            reconstructions.instruments.type_envelope(ChannelName.PULSE1, FeatureKey.VOLUME, first_raised(typed[0]))

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        def the_first_edit_lands_and_the_second_is_drawn_away(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the question about leaving")
            prompt.cancel()
            screen.expect(prompt.is_shown, operator.not_, description="the question answered")
            screen.expect(
                lambda: reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME),
                typed[0].__eq__,
                description="the field drawing the edit that landed",
            )
            assert screen.title() == titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))

        def leave_letting_it_go(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving again")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_and_close_while_the_rebuild_is_held,
            edit_again_after_the_close,
            the_first_edit_lands_and_the_second_is_drawn_away,
            leave_letting_it_go,
        ).run()
