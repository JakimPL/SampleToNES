import operator
from typing import Final, List, Tuple

import pytest

from automation.application.startup import Startup
from automation.boundaries.dialogs import DialogKind
from automation.screen import Screen
from automation.steps.reconstructions import (
    edited_title,
    expect_open,
    remove_from_the_browser,
    stored_levels,
    titled,
)
from automation.vocabulary.dialogs import CANCEL, CLOSE, CLOSE_MESSAGE, CLOSE_TITLE, SAVE
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.user import RECONSTRUCTIONS_DIRECTORY
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION

KEPT: Final[str] = "Kept.stn"
PULSES: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.PULSE2)
SETTLING_FRAMES: Final[int] = 10
NOT_APPLICABLE: Final[str] = "reconstructions.reconstruction.label.path_not_applicable"
RATE_SET_BY_THE_PROJECT: Final[str] = "reconstructions.reconstruction.tooltip.nes_frequency_locked"
RATE_KEPT_WITHOUT_A_FILE: Final[str] = "reconstructions.reconstruction.tooltip.nes_frequency_no_file"


def take_its_file_away(screen: Screen) -> None:
    """Removes the open reconstruction's file in the browser and waits for it to show as unsaved."""
    expect_open(screen, OPEN_RECONSTRUCTION)

    remove_from_the_browser(screen, OPEN_RECONSTRUCTION)

    screen.expect(
        screen.title, edited_title(screen, OPEN_RECONSTRUCTION).__eq__, description="the reconstruction left unsaved"
    )


class TestAReconstructionWhoseFileWasRemoved:
    """The open reconstruction whose file the browser removed stays open with nowhere to save, and asks where.

    Closing it asks first. Save asks where to write it, a dismissed dialog brings the question back
    once, and Cancel keeps it open.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Starts with the reconstruction open and no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_close_asks_where_a_dismissed_dialog_asks_once_and_cancel_keeps_it(self, screen: Screen) -> None:
        """The last Save names a file, which receives the reconstruction's levels.

        The removed file stays gone.
        """
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        kept = RECONSTRUCTIONS_DIRECTORY / KEPT
        standing: List[List[int]] = []

        def remove_it(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            standing.extend(stored_levels(OPEN_RECONSTRUCTION, channel) for channel in PULSES)

            take_its_file_away(screen)

            assert reconstructions.file_line() == screen.words(NOT_APPLICABLE)
            assert not reconstructions.can_save()

        def close_asks_first(screen: Screen) -> None:
            reconstructions.close_from_menu()

            screen.expect(prompt.is_shown, bool, description="the question about closing")
            assert prompt.title() == screen.words(CLOSE_TITLE)
            assert prompt.words() == screen.words(CLOSE_MESSAGE)
            assert prompt.answers() == (screen.words(SAVE), screen.words(CLOSE), screen.words(CANCEL))

        def save_asks_where_and_a_dismissed_dialog_asks_once_more(screen: Screen) -> None:
            screen.answer_next_dialog(DialogKind.SAVE, None)

            prompt.save()

            screen.expect(lambda: len(screen.dialog_requests()), bool, description="the save dialog asked")
            screen.expect(prompt.is_shown, bool, description="the question back")
            screen.frames(SETTLING_FRAMES)
            assert len(prompt.shown_windows()) == 1
            (request,) = screen.dialog_requests()
            assert request.kind is DialogKind.SAVE
            assert request.initial_directory == RECONSTRUCTIONS_DIRECTORY
            assert request.suggested_name == OPEN_RECONSTRUCTION.name

        def cancel_keeps_it_open(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == edited_title(screen, OPEN_RECONSTRUCTION)
            assert len(screen.dialog_requests()) == 1

        def save_where_asked_writes_it_and_closes(screen: Screen) -> None:
            reconstructions.close_from_menu()
            screen.expect(prompt.is_shown, bool, description="the question about closing again")
            screen.answer_next_dialog(DialogKind.SAVE, kept)

            prompt.save()

            screen.expect(screen.title, titled(screen).__eq__, description="the reconstruction closed")
            assert [stored_levels(kept, channel) for channel in PULSES] == standing
            assert not OPEN_RECONSTRUCTION.exists()

        screen.scenario(
            remove_it,
            close_asks_first,
            save_asks_where_and_a_dismissed_dialog_asks_once_more,
            cancel_keeps_it_open,
            save_where_asked_writes_it_and_closes,
        ).run()

    def test_the_locked_rate_says_nothing_of_a_project(self, screen: Screen) -> None:
        """The rate stays locked and its explanation words speak of the missing file, not of a project.

        Closing the reconstruction afterwards lets its changes go, so the application leaves with
        nothing to ask.
        """
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        take_its_file_away(screen)

        assert not reconstructions.can_retune()
        assert reconstructions.retune_lock_explained()
        assert reconstructions.retune_lock_words() != screen.words(RATE_SET_BY_THE_PROJECT)
        assert reconstructions.retune_lock_words() == screen.words(RATE_KEPT_WITHOUT_A_FILE)

        reconstructions.close_from_menu()
        screen.expect(prompt.is_shown, bool, description="the question about closing")
        prompt.confirm()

        screen.expect(screen.title, titled(screen).__eq__, description="the reconstruction let go")
