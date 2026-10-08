from automation.screen import Screen
from automation.steps.main import explorer_row, gather, home_path
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.main import TAG_MAIN_EXPLORER_BUTTON_REFRESH
from tests.screens.main.gathering.steps import gathered
from tests.suite.screens.seeds.constants import KICK


class TestGatheringARowRefreshBuiltAnew:
    """A recording Ctrl-clicked the moment Refresh brings its row back joins the list.

    Refresh takes the browser's rows down and builds them anew over a few frames, so the row of the
    recording comes back as a new row far below the top of a long browser. The scenario presses
    Refresh, waits for the row to come back and Ctrl-clicks it at once, expecting the recording in the
    list.
    """

    def test_the_rebuilt_row_gathers(self, screen: Screen) -> None:
        explorer = screen.explorer
        kick = home_path(KICK)

        def refresh(screen: Screen) -> None:
            before = explorer_row(screen, kick)

            screen.hand.click(compose_tag(TAG_MAIN_EXPLORER_BUTTON_REFRESH))

            screen.expect(lambda: explorer.file_row(kick), before.__ne__, description="the row taken down")

        def ctrl_click_the_row_it_brought_back(screen: Screen) -> None:
            gather(screen, kick)

            gathered(screen, kick)

        screen.scenario(refresh, ctrl_click_the_row_it_brought_back).run()
