from typing import Final, List

from sampletones_application.utils.gui.dialogs import DialogsRenderer
from tests.suite.frames import held_frames
from tests.suite.questions import StandingWindow, standing_window

__all__ = ["held_frames", "standing_window"]

TURN: Final[str] = "turn"


class TestTheWaitForTheScreen:
    """A guard waits for the screen through the renderer, as a turn in the modal line."""

    def test_a_turn_runs_at_once_on_a_free_screen(self) -> None:
        turns: List[str] = []

        DialogsRenderer.when_free(lambda: turns.append(TURN))

        assert turns == [TURN]

    def test_a_turn_runs_once_the_standing_window_leaves(self, standing_window: StandingWindow) -> None:
        turns: List[str] = []

        DialogsRenderer.when_free(lambda: turns.append(TURN))
        assert not turns
        standing_window.leave()

        assert turns == [TURN]
