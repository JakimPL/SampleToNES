import operator
from typing import List

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.screens.prompts.closing.constants import SETTLING_FRAMES
from tests.suite.screens.application.startup import Startup
from tests.suite.screens.holds.regeneration import RegenerationHold
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.reconstructions import (
    expect_open,
    first_raised,
    marked,
    raise_the_first_level_while_held,
    titled,
)
from tests.suite.screens.worlds.recordings import OPEN_RECONSTRUCTION


class TestClosingTheWindowWhileAnEditIsOnItsWay:
    """A close asked for during an edit asks about the edited reconstruction once the edit lands."""

    @pytest.fixture
    def startup(self) -> Startup:
        """Opens a reconstruction with no project."""
        return Startup(reconstruction=OPEN_RECONSTRUCTION, project=None)

    def test_two_closes_ask_once(self, screen: Screen, regeneration_hold: RegenerationHold) -> None:
        """Two closes during a held rebuild bring one question, Cancel leaves the screen quiet, and a
        further close asks again."""
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

        def close_once_more_and_leave(screen: Screen) -> None:
            screen.close_window()
            screen.expect(prompt.is_shown, bool, description="the question about leaving again")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            edit_and_close_twice_while_the_rebuild_is_held,
            the_edit_lands_and_one_question_comes,
            cancel_leaves_no_question,
            close_once_more_and_leave,
        ).run()

    def test_an_edit_made_after_the_close_is_drawn_away(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
    ) -> None:
        """An edit typed after the close is dropped, and the field shows the edit that landed."""
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
