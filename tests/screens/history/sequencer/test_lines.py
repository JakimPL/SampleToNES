from typing import Final, List

import pytest

from sampletones_application.categories.hierarchy import Tab
from tests.screens.history.steps import expect_lines, history_count
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go

NEWEST_LINE: Final[int] = 0
TEMPO: Final[int] = 120
STILL_FRAMES: Final[int] = 20
LOST_HIGHLIGHT: Final[str] = "A click on the History card's line in force takes its highlight off"


class TestAClickOnTheLineInForce:
    """A click on the line the project stands at keeps the project and the card as they were.

    The tempo is retyped, which adds a line in force. A click on that line leaves the tempo as typed and the
    line marked in force; a click on the oldest line then takes the tempo back, which witnesses the clicks.
    """

    @pytest.mark.xfail(strict=True, reason=LOST_HIGHLIGHT)
    def test_the_line_stays_in_force(self, screen: Screen) -> None:
        history = screen.sequencer.history
        module = screen.sequencer.module
        tempos: List[int] = []

        def retype_the_tempo(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            tempos.append(module.tempo())
            lines = history_count(screen)

            module.retype_tempo(TEMPO)

            expect_lines(screen, lines + 1)

        def click_the_line_in_force(screen: Screen) -> None:
            history.jump_to(NEWEST_LINE)
            screen.frames(STILL_FRAMES)

            assert module.tempo() == TEMPO
            assert history.lines()[NEWEST_LINE].current

        def click_the_oldest_line(screen: Screen) -> None:
            history.jump_to(history_count(screen) - 1)

            screen.expect(module.tempo, tempos[0].__eq__, description="the tempo as it stood")

        screen.scenario(
            retype_the_tempo,
            click_the_line_in_force,
            click_the_oldest_line,
            leave_letting_the_project_go,
        ).run()
