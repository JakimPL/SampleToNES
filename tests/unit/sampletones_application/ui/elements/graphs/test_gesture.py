import math
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.ui.elements.graphs import gesture as gesture_module
from sampletones_application.ui.elements.graphs.gesture import (
    DOUBLE_CLICK_SECONDS,
    PlotClickGesture,
)
from sampletones_shared.types.callback import VoidCallback

CLICK_TRAVEL: Final[float] = 4.0
DOUBLE_CLICK: Final[int] = 2
DOUBLE_CLICK_DISTANCE: Final[float] = 6.0
PRESS_SAMPLE: Final[float] = 420.6
PRESS_SCREEN: Final[Tuple[float, float]] = (300.0, 200.0)
TAP_SECONDS: Final[float] = 0.05


class Mouse:
    """The pointer and the clock as the gesture reads them, with the frames it waits on run by hand.

    Presses count up while each lands within the double-click window and distance of the one before
    it, and the press counted second is the double-click, as ImGui recognizes one: a third press in
    the same burst is none.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.time = 10.0
        self.sample = PRESS_SAMPLE
        self.screen = PRESS_SCREEN
        self.clicks = 0
        self._last_press: Optional[Tuple[float, Tuple[float, float]]] = None
        self._armed: List[VoidCallback] = []
        monkeypatch.setattr(gesture_module.dpg, "get_total_time", lambda: self.time)
        monkeypatch.setattr(gesture_module.dpg, "get_plot_mouse_pos", lambda: (self.sample, 0.0))
        monkeypatch.setattr(gesture_module.dpg, "get_mouse_pos", lambda local: self.screen)
        monkeypatch.setattr(
            gesture_module.dpg,
            "is_mouse_button_double_clicked",
            lambda button: self.clicks == DOUBLE_CLICK,
        )
        monkeypatch.setattr(
            gesture_module.FrameCallbackManager,
            "set_frame_callback",
            lambda callback, frame_count=1: self._armed.append(callback),
        )

    def wait(self, seconds: float) -> None:
        """Lets time pass, drawing the frames the gesture asked to be called back on."""
        self.time += seconds
        armed, self._armed = self._armed, []
        for callback in armed:
            callback()

    @property
    def waiting(self) -> int:
        """How many readings the gesture has asked the next frame for."""
        return len(self._armed)

    def press(self, gesture: PlotClickGesture) -> None:
        within = (
            self._last_press is not None
            and self.time - self._last_press[0] < DOUBLE_CLICK_SECONDS
            and math.dist(self.screen, self._last_press[1]) < DOUBLE_CLICK_DISTANCE
        )
        self.clicks = self.clicks + 1 if within else 1
        self._last_press = (self.time, self.screen)
        gesture.press()

    def tap(self, gesture: PlotClickGesture) -> None:
        self.press(gesture)
        self.time += TAP_SECONDS
        gesture.release()


@pytest.fixture
def mouse(monkeypatch: pytest.MonkeyPatch) -> Mouse:
    return Mouse(monkeypatch)


@pytest.fixture
def clicked() -> List[float]:
    return []


@pytest.fixture
def gesture(clicked: List[float]) -> PlotClickGesture:
    return PlotClickGesture(click_travel=CLICK_TRAVEL, on_clicked=clicked.append)


class TestAClickWaitsForTheDoubleClickWindow:
    """A click names its sample once the press it began with can no longer start a double-click."""

    def test_a_click_is_held_while_a_double_click_may_follow(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS / 2)

        assert clicked == []

    def test_a_click_reports_the_sample_under_its_press_once_the_window_closes(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS / 2)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == [PRESS_SAMPLE]

    def test_a_press_held_past_the_window_reports_as_it_comes_up(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.press(gesture)
        mouse.time += 2 * DOUBLE_CLICK_SECONDS
        gesture.release()

        assert clicked == [PRESS_SAMPLE]

    def test_a_click_within_the_travel_reports_the_sample_under_its_press(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.press(gesture)
        mouse.sample = PRESS_SAMPLE + 100
        mouse.screen = (PRESS_SCREEN[0] + CLICK_TRAVEL, PRESS_SCREEN[1])
        gesture.release()
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == [PRESS_SAMPLE]

    def test_a_press_landing_as_a_separate_click_reports_the_one_before_it(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.tap(gesture)
        mouse.sample = PRESS_SAMPLE + 300
        mouse.screen = (PRESS_SCREEN[0] + 10 * DOUBLE_CLICK_DISTANCE, PRESS_SCREEN[1])
        mouse.press(gesture)

        assert clicked == [PRESS_SAMPLE]


class TestADoubleClickReportsNothing:
    """The double-click fits the view, so neither of its clicks puts the playhead anywhere."""

    def test_neither_click_of_a_double_click_reports_a_sample(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.tap(gesture)
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == []

    def test_a_third_click_in_the_burst_reports_nothing(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        """ImGui counts the third press of a burst as no double-click, and it is still the burst."""
        mouse.tap(gesture)
        mouse.tap(gesture)
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == []

    def test_a_click_after_a_double_click_reports_its_own_sample(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.tap(gesture)
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        mouse.sample = PRESS_SAMPLE + 300
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == [PRESS_SAMPLE + 300]


class TestOneWaitStands:
    def test_clicks_in_turn_leave_one_reading_waiting(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        """A second click arriving while the first waits reports the first and joins the same wait."""
        mouse.tap(gesture)
        mouse.time += DOUBLE_CLICK_SECONDS
        mouse.sample = PRESS_SAMPLE + 300
        mouse.tap(gesture)

        assert (clicked, mouse.waiting) == ([PRESS_SAMPLE], 1)


class TestADragReportsNothing:
    def test_a_press_coming_up_past_the_travel_reports_nothing(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        mouse.press(gesture)
        mouse.screen = (PRESS_SCREEN[0] - 3 * CLICK_TRAVEL, PRESS_SCREEN[1])
        gesture.release()
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == []

    def test_a_release_with_no_press_on_the_plot_reports_nothing(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        gesture.release()
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == []
