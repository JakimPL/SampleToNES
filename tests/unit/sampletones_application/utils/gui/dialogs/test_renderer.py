from typing import Final, Iterator, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, SUF_BUTTON_OK, SUF_GROUP
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dialogs.renderer import FAILURE_REPORT_TAG
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.modal_queue import ModalQueue
from tests.suite.frames import Frames, held_frames
from tests.suite.questions import StandingWindow, standing_window
from tests.suite.shortcuts import shipped_source

__all__ = ["held_frames", "standing_window"]

TURN: Final[str] = "turn"
LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
REPORT_LINE: Final[str] = "the last action did not finish"
FIRST_FAILURE: Final[str] = "the first failure"
SECOND_FAILURE: Final[str] = "the second failure"
VIEWPORT_WIDTH: Final[int] = 1280
VIEWPORT_HEIGHT: Final[int] = 800


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


@pytest.fixture
def renderer(dpg_context: None, layout_config: LayoutConfig) -> DialogsRenderer:
    return DialogsRenderer(
        layout=layout_config.general,
        language_manager=LANGUAGE_MANAGER,
        status_bar=GUIStatusBar(display_time=layout_config.behavior.ui.status_bar_display_time),
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def reported_texts() -> List[str]:
    """The lines naming the failure the standing report shows."""
    return [str(dpg.get_value(item)) for item in dpg.get_item_children(compose_tag(FAILURE_REPORT_TAG, SUF_GROUP), 1)]


def dismiss_the_report() -> None:
    """Presses OK on the standing report."""
    dpg.get_item_callback(compose_tag(FAILURE_REPORT_TAG, SUF_BUTTON_OK, SUF_BUTTON))()


class TestTheFailureReport:
    """A failure nothing recovered from stands on the screen once, until the reader dismisses it."""

    @pytest.fixture(autouse=True)
    def viewport(self) -> Iterator[None]:
        """The viewport a report centers itself in, which a suite never opens."""
        with (
            patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
            patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
        ):
            yield

    @pytest.mark.usefixtures("held_frames")
    def test_a_report_stands_under_its_own_tag(self, renderer: DialogsRenderer) -> None:
        renderer.show_failure_report(RuntimeError(FIRST_FAILURE), REPORT_LINE)

        assert ModalQueue.snapshot().shown == FAILURE_REPORT_TAG
        assert FIRST_FAILURE in reported_texts()

    @pytest.mark.usefixtures("held_frames")
    def test_a_second_failure_leaves_the_first_report_standing(self, renderer: DialogsRenderer) -> None:
        renderer.show_failure_report(RuntimeError(FIRST_FAILURE), REPORT_LINE)

        renderer.show_failure_report(RuntimeError(SECOND_FAILURE), REPORT_LINE)

        assert FIRST_FAILURE in reported_texts()
        assert ModalQueue.snapshot().waiting == ()

    def test_a_failure_after_the_dismissal_is_reported_again(
        self,
        renderer: DialogsRenderer,
        held_frames: Frames,
    ) -> None:
        renderer.show_failure_report(RuntimeError(FIRST_FAILURE), REPORT_LINE)
        dismiss_the_report()

        renderer.show_failure_report(RuntimeError(SECOND_FAILURE), REPORT_LINE)
        held_frames.render()

        assert SECOND_FAILURE in reported_texts()

    def test_a_report_waits_behind_a_standing_window(
        self,
        renderer: DialogsRenderer,
        standing_window: StandingWindow,
    ) -> None:
        renderer.show_failure_report(RuntimeError(FIRST_FAILURE), REPORT_LINE)
        renderer.show_failure_report(RuntimeError(SECOND_FAILURE), REPORT_LINE)
        assert ModalQueue.snapshot().waiting == (FAILURE_REPORT_TAG,)

        standing_window.leave()

        assert FIRST_FAILURE in reported_texts()
