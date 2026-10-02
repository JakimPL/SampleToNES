import operator
from typing import Final, List

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.application import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.main import convert_alone, home_path
from tests.suite.screens.steps.project import retitle_project, saved_project_title
from tests.suite.screens.steps.reconstructions import (
    converted,
    expect_open,
    first_level_raised,
    leading,
    marked,
    raise_the_first_level,
    remove_from_the_browser,
    stored_levels,
    titled,
)
from tests.suite.screens.world import BASS, LEAD, OPEN_RECONSTRUCTION, SONG, SONG_INSTRUMENT, SONG_SAMPLE

RETITLED: Final[str] = "Retitled from the keyboard"
KEPT: Final[str] = "Kept.stn"
SETTLING_FRAMES: Final[int] = 10
EXIT_PROJECT_MESSAGE: Final[str] = "global.dialog.message.exit_unsaved_project"
EXIT_RECONSTRUCTION_MESSAGE: Final[str] = "global.dialog.message.exit_unsaved_reconstruction"
CLOSE_MESSAGE: Final[str] = "global.dialog.message.close_unsaved_reconstruction"


def tab(screen: Screen, times: int) -> None:
    for _ in range(times):
        screen.press_shortcut(ShortcutId.DIALOG_NEXT_CONTROL)


def enter(screen: Screen) -> None:
    screen.press_shortcut(ShortcutId.DIALOG_ACTIVATE)


def escape(screen: Screen) -> None:
    screen.press_shortcut(ShortcutId.DIALOG_CANCEL)


def edited_title(screen: Screen) -> str:
    return titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))


class TestTheExitChainFromTheKeyboard:
    """Tab, Enter and Escape answer the question about the reconstruction that the project's answer opens.

    Each question starts on Cancel, so one Tab reaches Save and two reach Exit.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_escape_on_the_second_keeps_everything_and_the_keys_then_save_and_leave(self, screen: Screen) -> None:
        project_prompt = screen.project.unsaved_prompt
        reconstruction_prompt = screen.reconstructions.unsaved_prompt
        stored: List[bytes] = []

        def open_the_project_and_change_both(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            stored.append(OPEN_RECONSTRUCTION.read_bytes())
            screen.answer_next_dialog(DialogKind.OPEN, SONG)
            screen.project.open()
            screen.expect(
                screen.sequencer.voices.names, [SONG_SAMPLE, SONG_INSTRUMENT].__eq__, description="the song's voices"
            )
            retitle_project(screen, RETITLED)

            raise_the_first_level(
                screen,
                ChannelName.PULSE1,
                title=titled(screen, marked(SONG.stem, unsaved=True), marked(OPEN_RECONSTRUCTION.name, unsaved=True)),
            )

        def exit_asks_about_the_project(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            screen.expect(project_prompt.is_shown, bool, description="the question about the project")
            assert project_prompt.words() == screen.words(EXIT_PROJECT_MESSAGE)

        def exit_on_the_project_asks_about_the_reconstruction(screen: Screen) -> None:
            tab(screen, 2)
            enter(screen)

            screen.expect(reconstruction_prompt.is_shown, bool, description="the question about the reconstruction")
            assert reconstruction_prompt.words() == screen.words(EXIT_RECONSTRUCTION_MESSAGE)
            assert not project_prompt.is_shown()

        def escape_keeps_the_application_and_both_changes(screen: Screen) -> None:
            escape(screen)

            screen.expect(reconstruction_prompt.is_shown, operator.not_, description="the question gone")
            screen.frames(SETTLING_FRAMES)
            assert screen.is_running()
            assert screen.shown_windows() == ()
            assert screen.title() == titled(
                screen, marked(SONG.stem, unsaved=True), marked(OPEN_RECONSTRUCTION.name, unsaved=True)
            )
            assert saved_project_title(SONG) != RETITLED
            assert OPEN_RECONSTRUCTION.read_bytes() == stored[0]

        def the_keys_save_the_project_and_leave(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(project_prompt.is_shown, bool, description="the question about the project again")
            tab(screen, 1)
            enter(screen)
            screen.expect(reconstruction_prompt.is_shown, bool, description="the question about the reconstruction")

            tab(screen, 2)
            enter(screen)

            assert screen.wait_for_exit()
            assert saved_project_title(SONG) == RETITLED
            assert OPEN_RECONSTRUCTION.read_bytes() == stored[0]

        screen.scenario(
            open_the_project_and_change_both,
            exit_asks_about_the_project,
            exit_on_the_project_asks_about_the_reconstruction,
            escape_keeps_the_application_and_both_changes,
            the_keys_save_the_project_and_leave,
        ).run()


class TestTheLoadChainFromTheKeyboard:
    """The keys answer Load at a run's end, and the question about unsaved changes that Load opens."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_escape_keeps_the_edits_and_the_keys_then_save_and_load(self, screen: Screen) -> None:
        converter = screen.main.converter
        prompt = screen.reconstructions.unsaved_prompt
        standing: List[int] = []

        def edit_the_open_reconstruction(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            standing.extend(stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1))

            raise_the_first_level(screen, ChannelName.PULSE1, title=edited_title(screen))

        def load_from_the_keyboard(screen: Screen, recording: str) -> None:
            convert_alone(
                screen,
                home_path(recording),
                channel=ChannelName.PULSE1,
                replacing=[home_path(BASS), home_path(LEAD)],
            )
            tab(screen, 1)
            enter(screen)

            screen.expect(prompt.is_shown, bool, description="the question about unsaved changes")
            assert not converter.end_prompt.is_shown()

        def escape_keeps_the_edited_one(screen: Screen) -> None:
            load_from_the_keyboard(screen, BASS)

            escape(screen)

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert screen.title() == edited_title(screen)
            assert screen.reconstructions.shows_open(OPEN_RECONSTRUCTION)

        def save_and_load_from_the_keyboard(screen: Screen) -> None:
            load_from_the_keyboard(screen, LEAD)

            tab(screen, 1)
            enter(screen)

            expect_open(screen, converted(home_path(LEAD)))
            saved = stored_levels(OPEN_RECONSTRUCTION, ChannelName.PULSE1)
            assert leading(saved, standing) == first_level_raised(standing)

        screen.scenario(
            edit_the_open_reconstruction,
            escape_keeps_the_edited_one,
            save_and_load_from_the_keyboard,
        ).run()


class TestASaveThatAsksWhereFromTheKeyboard:
    """The question a dismissed save dialog brings back answers to the keys like the first one."""

    @pytest.fixture
    def startup(self) -> Startup:
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_escape_on_the_returned_question_then_the_keys_save_where_asked(self, screen: Screen) -> None:
        prompt = screen.reconstructions.unsaved_prompt
        kept = RECONSTRUCTIONS_DIRECTORY / KEPT

        def take_its_file_away(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

            screen.expect(screen.title, edited_title(screen).__eq__, description="the reconstruction left unsaved")

        def save_asks_where_and_a_dismissed_dialog_asks_again(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)
            screen.expect(prompt.is_shown, bool, description="the question about closing")
            assert prompt.words() == screen.words(CLOSE_MESSAGE)
            screen.answer_next_dialog(DialogKind.SAVE, None)

            tab(screen, 1)
            enter(screen)

            screen.expect(lambda: len(screen.dialog_requests()), bool, description="the save dialog asked")
            screen.expect(prompt.is_shown, bool, description="the question back")
            assert len(prompt.shown_windows()) == 1

        def escape_keeps_it_open(screen: Screen) -> None:
            escape(screen)

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            screen.frames(SETTLING_FRAMES)
            assert screen.title() == edited_title(screen)
            assert screen.shown_windows() == ()

        def the_keys_save_it_where_asked_and_close_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.CLOSE_RECONSTRUCTION)
            screen.expect(prompt.is_shown, bool, description="the question about closing again")
            screen.answer_next_dialog(DialogKind.SAVE, kept)

            tab(screen, 1)
            enter(screen)

            screen.expect(screen.title, titled(screen).__eq__, description="the reconstruction closed")
            assert kept.exists()
            assert not prompt.is_shown()

        screen.scenario(
            take_its_file_away,
            save_asks_where_and_a_dismissed_dialog_asks_again,
            escape_keeps_it_open,
            the_keys_save_it_where_asked_and_close_it,
        ).run()


class TestTheDisplayQuestionFromTheKeyboard:
    """The question Escape asks of changed Display settings answers to the keys, as does the dialog after it."""

    def test_enter_keeps_editing_and_tab_enter_discards(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt
        original: List[bool] = []

        def change_vertical_sync(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the Display settings dialog")
            original.append(settings.vsync())

            settings.toggle_vsync()

            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

        def escape_asks(screen: Screen) -> None:
            escape(screen)

            screen.expect(prompt.is_shown, bool, description="the discard question")

        def enter_keeps_editing(screen: Screen) -> None:
            enter(screen)

            screen.expect(settings.is_shown, bool, description="the dialog back")
            assert not prompt.is_shown()
            assert settings.vsync() != original[0]

        def escape_then_tab_and_enter_discard(screen: Screen) -> None:
            escape(screen)
            screen.expect(prompt.is_shown, bool, description="the discard question again")

            tab(screen, 1)
            enter(screen)

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert not settings.is_shown()
            settings.open()
            screen.expect(settings.is_shown, bool, description="the dialog opened again")
            assert settings.vsync() == original[0]
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="the unchanged dialog closed")

        screen.scenario(change_vertical_sync, escape_asks, enter_keeps_editing, escape_then_tab_and_enter_discard).run()
