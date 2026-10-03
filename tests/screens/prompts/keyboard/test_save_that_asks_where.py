import operator
from typing import Final

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.screens.prompts.keyboard.constants import SETTLING_FRAMES
from tests.screens.prompts.keyboard.steps import enter, escape, tab
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.boundaries.dialogs import DialogKind
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import edited_title, expect_open, remove_from_the_browser, titled
from tests.suite.screens.vocabulary.dialogs import CLOSE_MESSAGE
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION

KEPT: Final[str] = "Kept.stn"


class TestASaveThatAsksWhereFromTheKeyboard:
    """The question a dismissed save dialog brings back answers to the keys like the first one.

    The open reconstruction loses its file in the browser, so closing it asks and Save asks where to write.
    The save dialog is dismissed and the question returns. Escape keeps the reconstruction open. Closing
    again, the keys choose Save, the save dialog names a file, and the reconstruction is written there and
    closed.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Starts with the reconstruction open and no project."""
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
