import os
from typing import Final

import pytest

from automation.application.startup import Startup
from automation.environment import repeats
from automation.holds.regeneration import RegenerationHold
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from automation.worlds.home import World
from sampletones_core.constants.enums import ChannelName, FeatureKey
from tests.suite.screens.worlds.recordings import LONG_RECONSTRUCTION, long_document_world

DRAGGED_ITEM: Final[int] = 3
QUIET: Final[float] = 2.0
NEAR_THE_START: Final[float] = 0.05
ZOOM_NOTCHES: Final[int] = 5
REPEATS: Final[int] = repeats(os.environ)


class TestClosingWhileALongRebuildRuns:
    """Closing the window the moment a two-minute document's rebuild is let go waits for it and leaves.

    A volume bar is dragged while the rebuild is held, so the rebuild is released and the close asked
    for in one breath, and the close meets the rebuild on its worker. The application waits for the
    edit, asks about the unsaved document, and leaves on the answer. The scenario runs as many times
    as ``SAMPLETONES_SCREENS_REPEATS`` says, which is how a change to the worker's work is held to a
    clean exit over and over.
    """

    @pytest.fixture
    def world(self) -> World:
        """The home holds the two-minute reconstruction with its recording."""
        return long_document_world()

    @pytest.fixture
    def startup(self) -> Startup:
        """The two-minute reconstruction is open at start, with no project."""
        return Startup(reconstruction=LONG_RECONSTRUCTION, project=None)

    @pytest.mark.parametrize("attempt", range(REPEATS))
    def test_the_close_waits_for_the_rebuild_and_leaves(
        self,
        screen: Screen,
        regeneration_hold: RegenerationHold,
        attempt: int,
    ) -> None:
        """The question about the edited document comes once the rebuild lands, and confirming it leaves."""
        prompt = screen.reconstructions.unsaved_prompt
        instruments = screen.reconstructions.instruments
        graph = instruments.graph(ChannelName.PULSE1, FeatureKey.VOLUME)

        def drag_while_the_rebuild_is_held(screen: Screen) -> None:
            expect_open(screen, LONG_RECONSTRUCTION)
            instruments.bring_forward(ChannelName.PULSE1)
            screen.hand.scroll_into_view(graph.plot)
            graph.zoom_in(NEAR_THE_START, ZOOM_NOTCHES)
            standing = instruments.envelope_items(ChannelName.PULSE1, FeatureKey.VOLUME)

            graph.drag_item(DRAGGED_ITEM, start=standing[DRAGGED_ITEM], end=QUIET)

            screen.expect(regeneration_hold.waiting, bool, description="the rebuild held")

        def release_and_close_at_once(screen: Screen) -> None:
            regeneration_hold.release()
            screen.close_window()

        def the_question_comes_and_the_application_leaves(screen: Screen) -> None:
            screen.expect(prompt.is_shown, bool, description="the question about the edited reconstruction")

            prompt.confirm()

            assert screen.wait_for_exit()

        screen.scenario(
            drag_while_the_rebuild_is_held,
            release_and_close_at_once,
            the_question_comes_and_the_application_leaves,
        ).run()
