import operator
from typing import Final, List

import pytest

from automation.application.startup import Startup
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.reconstructions import (
    expect_open,
    load_from_the_browser,
    marked,
    raise_the_first_level_while_held,
    remove_from_the_browser,
    titled,
)
from automation.vocabulary.dialogs import CLOSE_TITLE, LOAD_TITLE
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.prompts.modals.constants import SETTLING_FRAMES
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION, OTHER_RECONSTRUCTION

REBUILD_FAILURE: Final[str] = "The rebuild broke on its worker"


class RebuildBrokeError(RuntimeError):
    """The failure a held rebuild is let go with, standing for a rebuild that raised."""


class TestTwoGesturesWaitingOnAHeldRebuild:
    """A load and a close asked for while an edit is on its way each ask their question once it lands, in
    order.

    A first level is raised while the rebuild is held, then a load and a close are asked for. Both wait;
    when the rebuild is released the load asks first, Cancel brings the close's question, and Cancel again
    leaves the edited reconstruction open.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction with no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_their_questions_come_one_after_the_other(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        """The load asks first, the close asks next, and then the screen is quiet."""
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        typed: List[str] = []

        def edit_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)

            typed.append(raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1))

        def load_and_close_while_it_is_held(screen: Screen) -> None:
            load_from_the_browser(screen, OTHER_RECONSTRUCTION)
            reconstructions.close_from_menu()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert reconstructions.shows_open(OPEN_RECONSTRUCTION)

        def the_load_asks_first(screen: Screen) -> None:
            regeneration_hold.release()

            screen.expect(prompt.is_shown, bool, description="the first question")
            assert prompt.title() == screen.words(LOAD_TITLE)
            assert len(screen.shown_windows()) == 1

        def the_close_asks_next(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.title, screen.words(CLOSE_TITLE).__eq__, description="the second question")
            assert len(screen.shown_windows()) == 1

        def nothing_asks_after_them(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the questions answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert screen.title() == titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True))
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == typed[0]

        def leave_letting_it_go(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_while_the_rebuild_is_held,
            load_and_close_while_it_is_held,
            the_load_asks_first,
            the_close_asks_next,
            nothing_asks_after_them,
            leave_letting_it_go,
        ).run()


class TestAFailedRebuildBeforeAClose:
    """A rebuild that fails while a close waits on it reports the failure first, and the close asks after.

    The open reconstruction loses its file, its first level is raised while the rebuild is held, and a
    close is asked for. The rebuild fails; the failure shows alone, and once it is dismissed the close
    asks. Cancel keeps the reconstruction as it stood.
    """

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction with no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_the_failure_first_and_the_question_after(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        """The failure shows first and the close asks once the failure is dismissed."""
        reconstructions = screen.reconstructions
        prompt = reconstructions.unsaved_prompt
        notice = screen.error_notice
        standing: List[str] = []

        def edit_a_removed_reconstruction_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, OPEN_RECONSTRUCTION)
            remove_from_the_browser(screen, OPEN_RECONSTRUCTION)
            screen.expect(
                screen.title,
                titled(screen, marked(OPEN_RECONSTRUCTION.name, unsaved=True)).__eq__,
                description="the reconstruction left unsaved",
            )
            standing.append(reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME))

            raise_the_first_level_while_held(screen, regeneration_hold, ChannelName.PULSE1)

        def close_while_it_is_held(screen: Screen) -> None:
            reconstructions.close_from_menu()

            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()

        def the_failure_comes_first(screen: Screen) -> None:
            regeneration_hold.fail(RebuildBrokeError(REBUILD_FAILURE))

            screen.expect(notice.is_shown, bool, description="the failure reported")
            screen.claim_error(RebuildBrokeError.__name__)
            screen.frames(SETTLING_FRAMES)
            assert not prompt.is_shown()
            assert len(screen.shown_windows()) == 1

        def the_question_comes_once_the_failure_is_read(screen: Screen) -> None:
            notice.dismiss()

            screen.expect(prompt.is_shown, bool, description="the question about closing")
            assert prompt.title() == screen.words(CLOSE_TITLE)

        def cancel_keeps_the_reconstruction_as_it_stood(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(prompt.is_shown, operator.not_, description="the question answered")
            screen.frames(SETTLING_FRAMES)
            assert screen.shown_windows() == ()
            assert reconstructions.instruments.envelope(ChannelName.PULSE1, FeatureKey.VOLUME) == standing[0]

        def leave_letting_it_go(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)
            screen.expect(prompt.is_shown, bool, description="the question about leaving")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_a_removed_reconstruction_while_the_rebuild_is_held,
            close_while_it_is_held,
            the_failure_comes_first,
            the_question_comes_once_the_failure_is_read,
            cancel_keeps_the_reconstruction_as_it_stood,
            leave_letting_it_go,
        ).run()
