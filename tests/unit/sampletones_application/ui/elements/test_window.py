from typing import Any, Final, Iterator, Optional
from unittest.mock import MagicMock, patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.primitives import DEARPYGUI_MAXIMUM_WINDOW_SIZE, DialogGeometry
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_shared.types.callback import VoidCallback
from tests.suite.frames import Frames, held_frames

MODULE: Final[str] = "sampletones_application.ui.elements.window"
TAG: Final[str] = "test.dialog.window.probe"
OTHER_TAG: Final[str] = "test.dialog.window.other"
PROMPT_TAG: Final[str] = "test.dialog.window.prompt"
REPORT_TAG: Final[str] = "test.dialog.window.report"
STATED_WIDTH: Final[int] = 460
STATED_HEIGHT: Final[int] = 200
VIEWPORT_WIDTH: Final[int] = 1280
VIEWPORT_HEIGHT: Final[int] = 800

__all__ = ["held_frames"]


class ProbeWindow(GUIWindow):
    """A dialog whose content stretches across the window, the shape a stated width has to hold."""

    def __init__(
        self,
        on_close: Optional[VoidCallback],
        geometry: Optional[DialogGeometry] = None,
        tag: str = TAG,
    ) -> None:
        self._on_close = on_close
        super().__init__(
            tag=tag,
            geometry=geometry if geometry is not None else DialogGeometry(width=STATED_WIDTH, height=STATED_HEIGHT),
        )

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The probe carries no state to seed."""

    def create_window(self) -> None:
        with self.dialog_window(
            label="probe",
            on_close=self._on_close,
        ):
            dpg.add_combo(items=["a", "b"], width=-1)


class ReportingWindow(ProbeWindow):
    """A window reporting work under way, which leaves the rest of the interface live beside it."""

    _claims_the_screen = False

    def __init__(self) -> None:
        super().__init__(on_close=None, tag=REPORT_TAG)


@pytest.fixture(name="dpg_context")
def dpg_context_fixture() -> Iterator[None]:
    dpg.create_context()
    try:
        yield
    finally:
        dpg.destroy_context()


class TestDialogGeometry:
    def test_the_window_holds_the_width_it_states(self, dpg_context: None) -> None:
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["width"] == STATED_WIDTH

    def test_the_window_holds_its_stated_width_both_ways(self, dpg_context: None) -> None:
        """A window free to widen, holding content measured against its width, widens every frame.

        The probe's combo stretches across the window, so the width it asks for follows the width
        the window has; holding the window to one width is what leaves the two agreeing.
        """
        ProbeWindow(on_close=None).create_window()

        configuration = dpg.get_item_configuration(TAG)
        assert configuration["autosize"] is True
        assert configuration["min_size"][0] == STATED_WIDTH
        assert configuration["max_size"][0] == STATED_WIDTH

    def test_the_window_leaves_its_height_to_what_it_holds(self, dpg_context: None) -> None:
        """A prompt wrapping over several lines grows down, so nothing caps the height."""
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["max_size"][1] == DEARPYGUI_MAXIMUM_WINDOW_SIZE

    def test_the_window_opens_at_the_height_it_states(self, dpg_context: None) -> None:
        """A dialog holding more than it states grows, so the stated height is where it starts."""
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["min_size"][1] == STATED_HEIGHT

    def test_a_window_stating_no_height_leaves_its_content_to_settle_it(self, dpg_context: None) -> None:
        ProbeWindow(on_close=None, geometry=DialogGeometry(width=STATED_WIDTH)).create_window()

        assert dpg.get_item_configuration(TAG)["min_size"][1] == 0


class TestWhereADialogOpens:
    """A dialog stating a height is placed before it is drawn, so it never appears off center."""

    @staticmethod
    def _shown(geometry: DialogGeometry) -> Any:
        window = ProbeWindow(on_close=None, geometry=geometry)
        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled"),
            patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
            patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
        ):
            window.show()

        return dpg.get_item_pos(TAG)

    def test_a_window_stating_a_height_stands_at_its_center(self, dpg_context: None) -> None:
        position = self._shown(DialogGeometry(width=STATED_WIDTH, height=STATED_HEIGHT))

        assert position == [
            (VIEWPORT_WIDTH - STATED_WIDTH) // 2,
            (VIEWPORT_HEIGHT - STATED_HEIGHT) // 2,
        ]

    def test_a_window_taller_than_the_viewport_keeps_its_title_bar_reachable(self, dpg_context: None) -> None:
        position = self._shown(DialogGeometry(width=STATED_WIDTH, height=VIEWPORT_HEIGHT * 2))

        assert position[1] == 0

    def test_a_window_settling_its_own_height_is_left_to_the_correction(self, dpg_context: None) -> None:
        """Nothing states where it goes until a frame has measured it, so the pass does the placing."""
        window = ProbeWindow(on_close=None, geometry=DialogGeometry(width=STATED_WIDTH))

        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled") as center_when_settled,
            patch.object(dpg, "set_item_pos") as set_item_pos,
        ):
            window.show()

        set_item_pos.assert_not_called()
        center_when_settled.assert_called_once_with(TAG)


class TestCloseAffordance:
    def test_a_dialog_answering_for_its_close_offers_the_button(self, dpg_context: None) -> None:
        ProbeWindow(on_close=lambda: None).create_window()

        assert dpg.get_item_configuration(TAG)["no_close"] is False

    def test_a_dialog_answering_for_no_close_omits_the_button(self, dpg_context: None) -> None:
        ProbeWindow(on_close=None).create_window()

        assert dpg.get_item_configuration(TAG)["no_close"] is True


class TestModalHandOff:
    """DearPyGui carries one modal at a time, so a dialog raising another has to step aside first."""

    @pytest.fixture(name="window")
    def window_fixture(self, dpg_context: None) -> Iterator[ProbeWindow]:
        """A dialog raised the way every dialog is, holding the screen."""
        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled"),
            patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
            patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
        ):
            window = ProbeWindow(on_close=None)
            window.show()
            yield window

    def test_yielding_takes_the_window_off_screen(self, window: ProbeWindow, held_frames: Frames) -> None:
        window.yield_to(MagicMock())

        assert dpg.get_item_configuration(TAG)["show"] is False

    def test_the_modal_is_raised_a_frame_after_the_hand_off(self, window: ProbeWindow, held_frames: Frames) -> None:
        """A modal built while this window still holds the screen opens where nobody can reach it."""
        raise_modal = MagicMock()

        window.yield_to(raise_modal)
        raise_modal.assert_not_called()
        held_frames.render()

        raise_modal.assert_called_once_with()

    def test_resuming_waits_a_frame_before_taking_the_screen_back(
        self,
        window: ProbeWindow,
        held_frames: Frames,
    ) -> None:
        window.yield_to(MagicMock())
        held_frames.render()

        window.resume()
        assert dpg.get_item_configuration(TAG)["show"] is False
        held_frames.render()

        assert dpg.get_item_configuration(TAG)["show"] is True

    def test_the_widget_tree_survives_the_hand_off(self, window: ProbeWindow, held_frames: Frames) -> None:
        """Whatever is being edited has to still be there when the dialog comes back."""
        window.yield_to(MagicMock())

        assert dpg.get_item_children(TAG, 1)

    def test_leaving_deletes_the_window(self, window: ProbeWindow, held_frames: Frames) -> None:
        window._leave_then(MagicMock())

        assert not dpg.does_item_exist(TAG)

    def test_the_answer_runs_a_frame_after_the_window_left(self, window: ProbeWindow, held_frames: Frames) -> None:
        answer = MagicMock()

        window._leave_then(answer)
        answer.assert_not_called()
        held_frames.render()

        answer.assert_called_once_with()

    def test_a_window_that_already_left_answers_nothing(self, window: ProbeWindow, held_frames: Frames) -> None:
        """A second click reaches a window gone from the screen, and only the first one answers."""
        first = MagicMock()
        second = MagicMock()

        window._leave_then(first)
        window._leave_then(second)
        held_frames.render()

        first.assert_called_once_with()
        second.assert_not_called()


class TestOneModalAtATime:
    """A modal asked for while another conversation holds the screen opens once that one has ended."""

    @pytest.fixture(name="viewport", autouse=True)
    def viewport_fixture(self) -> Iterator[None]:
        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled"),
            patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
            patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
        ):
            yield

    def test_a_window_asked_for_while_another_stands_waits_for_it_to_leave(
        self,
        dpg_context: None,
        held_frames: Frames,
    ) -> None:
        standing = ProbeWindow(on_close=None)
        waiting = ProbeWindow(on_close=None, tag=OTHER_TAG)
        standing.show()

        waiting.show()
        held_frames.render()
        assert not dpg.does_item_exist(OTHER_TAG)

        standing.hide()
        held_frames.render()

        assert dpg.does_item_exist(OTHER_TAG)

    def test_what_an_answer_raises_opens_ahead_of_a_waiting_window(
        self,
        dpg_context: None,
        held_frames: Frames,
    ) -> None:
        standing = ProbeWindow(on_close=None)
        waiting = ProbeWindow(on_close=None, tag=OTHER_TAG)
        prompt = ProbeWindow(on_close=None, tag=PROMPT_TAG)
        standing.show()
        waiting.show()

        standing._leave_then(prompt.show)
        held_frames.render()

        assert dpg.does_item_exist(PROMPT_TAG)
        assert not dpg.does_item_exist(OTHER_TAG)

    def test_a_window_reporting_work_under_way_opens_beside_a_modal(self, dpg_context: None) -> None:
        """A window leaving the rest of the interface live is not a modal, so it waits for nothing."""
        ProbeWindow(on_close=None).show()

        ReportingWindow().show()

        assert dpg.does_item_exist(REPORT_TAG)

    def test_showing_a_standing_window_again_rebuilds_it_a_frame_later(
        self,
        dpg_context: None,
        held_frames: Frames,
    ) -> None:
        window = ProbeWindow(on_close=None)
        window.show()

        window.show()
        assert not dpg.does_item_exist(TAG)
        held_frames.render()

        assert dpg.does_item_exist(TAG)


class TestRaisingAWindow:
    """A window is raised from wherever a result reaches the screen, the callback drain between
    frames included, so opening one waits on no frame."""

    @pytest.fixture(name="viewport", autouse=True)
    def viewport_fixture(self) -> Iterator[None]:
        """Stands in for the viewport a window is centered against, which a suite draws none of."""
        with (
            patch.object(dpg, "get_viewport_client_width", return_value=VIEWPORT_WIDTH),
            patch.object(dpg, "get_viewport_client_height", return_value=VIEWPORT_HEIGHT),
        ):
            yield

    def test_opening_waits_on_no_frame(self, dpg_context: None) -> None:
        window = ProbeWindow(on_close=None)

        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled"),
            patch.object(dpg, "split_frame") as split_frame,
        ):
            window.show()

        split_frame.assert_not_called()

    def test_opening_centers_the_window_once_it_has_been_measured(self, dpg_context: None) -> None:
        window = ProbeWindow(on_close=None)

        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled") as center_when_settled,
        ):
            window.show()

        center_when_settled.assert_called_once_with(TAG)

    def test_opening_builds_the_tree(self, dpg_context: None) -> None:
        window = ProbeWindow(on_close=None)

        with (
            patch(f"{MODULE}.ThemeRegistry"),
            patch(f"{MODULE}.center_when_settled"),
        ):
            window.show()

        assert dpg.get_item_children(TAG, 1)
