from typing import Final, List, Tuple

import pytest

from sampletones_application.ui.elements.graphs import click as click_module
from sampletones_application.ui.elements.graphs.click import (
    DOUBLE_CLICK_SECONDS,
    PlotClickGesture,
)
from sampletones_shared.types.callback import VoidCallback

CLICK_TRAVEL: Final[float] = 4.0
PRESS_SAMPLE: Final[float] = 420.6
PRESS_SCREEN: Final[Tuple[float, float]] = (300.0, 200.0)
TAP_SECONDS: Final[float] = 0.05


class Mouse:
    """The pointer and the clock as the gesture reads them, with the frames it waits on run by hand.

    A press within the double-click window of the one before it, at the spot it went down, is the
    second half of a double-click, as ImGui recognizes one.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.time = 10.0
        self.sample = PRESS_SAMPLE
        self.screen = PRESS_SCREEN
        self.double_clicked = False
        self._armed: List[VoidCallback] = []
        monkeypatch.setattr(click_module.dpg, "get_total_time", lambda: self.time)
        monkeypatch.setattr(click_module.dpg, "get_plot_mouse_pos", lambda: (self.sample, 0.0))
        monkeypatch.setattr(click_module.dpg, "get_mouse_pos", lambda local: self.screen)
        monkeypatch.setattr(
            click_module.dpg,
            "is_mouse_button_double_clicked",
            lambda button: self.double_clicked,
        )
        monkeypatch.setattr(
            click_module.FrameCallbackManager,
            "set_frame_callback",
            lambda callback, frame_count=1: self._armed.append(callback),
        )

    def wait(self, seconds: float) -> None:
        """Lets time pass, drawing the frames the gesture asked to be called back on."""
        self.time += seconds
        armed, self._armed = self._armed, []
        for callback in armed:
            callback()

    def tap(self, gesture: PlotClickGesture) -> None:
        gesture.press()
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
        gesture.press()
        mouse.time += 2 * DOUBLE_CLICK_SECONDS
        gesture.release()

        assert clicked == [PRESS_SAMPLE]

    def test_a_click_within_the_travel_reports_the_sample_under_its_press(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        gesture.press()
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
        gesture.press()

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
        mouse.double_clicked = True
        mouse.tap(gesture)
        mouse.double_clicked = False
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
        mouse.double_clicked = True
        mouse.tap(gesture)
        mouse.double_clicked = False
        mouse.wait(DOUBLE_CLICK_SECONDS)

        mouse.sample = PRESS_SAMPLE + 300
        mouse.tap(gesture)
        mouse.wait(DOUBLE_CLICK_SECONDS)

        assert clicked == [PRESS_SAMPLE + 300]


class TestADragReportsNothing:
    def test_a_press_coming_up_past_the_travel_reports_nothing(
        self,
        mouse: Mouse,
        gesture: PlotClickGesture,
        clicked: List[float],
    ) -> None:
        gesture.press()
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
