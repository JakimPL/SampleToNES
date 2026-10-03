import operator
from typing import Final, List

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName
from tests.screens.prompts.keyboard.constants import SETTLING_FRAMES
from tests.screens.prompts.keyboard.steps import enter, escape, tab
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.project import retitle_project, saved_project_title
from tests.suite.screens.steps.reconstructions import expect_open, marked, raise_the_first_level, titled
from tests.suite.screens.vocabulary.dialogs import EXIT_PROJECT_MESSAGE, EXIT_RECONSTRUCTION_MESSAGE
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, SONG, SONG_INSTRUMENT, SONG_SAMPLE

RETITLED: Final[str] = "Retitled from the keyboard"


class TestTheExitChainFromTheKeyboard:
    """Tab, Enter and Escape answer the question about the reconstruction that the project's answer opens.

    Each question starts on Cancel, so one Tab reaches Save and two reach Exit. The scenario opens a
    project beside an edited reconstruction and retitles the project. Exit asks about the project, and Exit
    on that question asks about the reconstruction. Escape there keeps the application and both changes.
    Then the keys save the project, leave the reconstruction's file as it was, and close the application.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Starts with the reconstruction open and no project."""
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
