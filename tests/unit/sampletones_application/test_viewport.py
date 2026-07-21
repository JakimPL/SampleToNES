from dataclasses import dataclass, field
from typing import List, Tuple

import pytest
from screeninfo import Monitor

from sampletones_application.viewport import _MAX_WINDOW_MONITOR_RATIO, ViewportManager

_TOGGLE_FULLSCREEN = "dearpygui.dearpygui.toggle_viewport_fullscreen"

_PRIMARY = Monitor(x=0, y=0, width=1920, height=1080)
_SECONDARY = Monitor(x=1920, y=0, width=2560, height=1440)

_MIN_WIDTH = 1024
_MIN_HEIGHT = 640


def _manager() -> ViewportManager:
    manager = ViewportManager.__new__(ViewportManager)
    manager._min_width = _MIN_WIDTH
    manager._min_height = _MIN_HEIGHT
    return manager


def _usable_bounds(monitor: Monitor) -> Tuple[int, int, int, int]:
    usable_width = int(monitor.width * _MAX_WINDOW_MONITOR_RATIO)
    usable_height = int(monitor.height * _MAX_WINDOW_MONITOR_RATIO)
    margin_x = (monitor.width - usable_width) // 2
    margin_y = (monitor.height - usable_height) // 2
    return usable_width, usable_height, margin_x, margin_y


@dataclass(frozen=True)
class FitCase:
    name: str
    monitors: Tuple[Monitor, ...]
    target: Monitor
    x: int
    y: int
    width: int
    height: int


_FIT_CASES = (
    FitCase("oversized_from_larger_monitor", (_PRIMARY,), _PRIMARY, 200, 200, 2560, 1440),
    FitCase("equal_to_monitor", (_PRIMARY,), _PRIMARY, 0, 0, 1920, 1080),
    FitCase("off_screen_top_left", (_PRIMARY,), _PRIMARY, -500, -500, 1280, 800),
    FitCase("off_screen_bottom_right", (_PRIMARY,), _PRIMARY, 5000, 5000, 1280, 800),
    FitCase("on_secondary_monitor", (_PRIMARY, _SECONDARY), _SECONDARY, 2000, 100, 4000, 3000),
)


class TestFitWindowToMonitor:
    @pytest.mark.parametrize("case", _FIT_CASES, ids=lambda case: case.name)
    def test_result_stays_within_usable_area(
        self,
        case: FitCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "sampletones_application.viewport.get_monitors",
            lambda: list(case.monitors),
        )
        manager = _manager()

        x, y, width, height = manager._fit_window_to_monitor(case.x, case.y, case.width, case.height)

        usable_width, usable_height, margin_x, margin_y = _usable_bounds(case.target)
        assert width <= usable_width
        assert height <= usable_height
        assert x >= case.target.x + margin_x
        assert y >= case.target.y + margin_y
        assert x + width <= case.target.x + case.target.width - margin_x
        assert y + height <= case.target.y + case.target.height - margin_y

    def test_window_that_already_fits_is_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sampletones_application.viewport.get_monitors",
            lambda: [_PRIMARY],
        )
        manager = _manager()

        assert manager._fit_window_to_monitor(300, 200, 1280, 800) == (300, 200, 1280, 800)

    def test_monitor_sized_window_is_shrunk_below_monitor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sampletones_application.viewport.get_monitors",
            lambda: [_PRIMARY],
        )
        manager = _manager()

        _, _, width, height = manager._fit_window_to_monitor(0, 0, _PRIMARY.width, _PRIMARY.height)

        assert width < _PRIMARY.width
        assert height < _PRIMARY.height

    def test_window_below_minimum_is_held_at_minimum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sampletones_application.viewport.get_monitors",
            lambda: [_PRIMARY],
        )
        manager = _manager()

        _, _, width, height = manager._fit_window_to_monitor(300, 200, 800, 500)

        assert width >= _MIN_WIDTH
        assert height >= _MIN_HEIGHT

    def test_falls_back_to_screen_dimensions_without_monitors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sampletones_application.viewport.get_monitors",
            list,
        )
        manager = _manager()
        manager._get_screen_dimensions = lambda: (1920, 1080)  # type: ignore[method-assign]

        x, y, width, height = manager._fit_window_to_monitor(200, 200, 4000, 4000)

        assert 0 <= x and 0 <= y
        assert x + width <= 1920
        assert y + height <= 1080


@dataclass
class FakeSession:
    fullscreen: bool = False
    window_x: int = 100
    window_y: int = 120
    window_width: int = 1280
    window_height: int = 800
    set_calls: List[bool] = field(default_factory=list)

    def set_window_state(self, *, fullscreen: bool, x: int, y: int, width: int, height: int) -> None:
        self.set_calls.append(fullscreen)
        self.fullscreen = fullscreen


def _fullscreen_manager(session: FakeSession, changes: List[int]) -> ViewportManager:
    manager = ViewportManager.__new__(ViewportManager)
    manager._session_manager = session  # type: ignore[assignment]
    manager._on_fullscreen_state_changed = lambda: changes.append(1)  # type: ignore[assignment]
    return manager


@dataclass(frozen=True)
class ToggleCase:
    name: str
    initial: bool
    expect_fullscreen: bool


_TOGGLE_CASES = (
    ToggleCase("enters_from_windowed", False, True),
    ToggleCase("exits_from_fullscreen", True, False),
)


class TestToggleFullscreen:
    @pytest.mark.parametrize("case", _TOGGLE_CASES, ids=lambda case: case.name)
    def test_toggle_flips_dpg_and_session_together(
        self,
        case: ToggleCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        toggles: List[int] = []
        monkeypatch.setattr(_TOGGLE_FULLSCREEN, lambda: toggles.append(1))
        session = FakeSession(fullscreen=case.initial)
        changes: List[int] = []
        manager = _fullscreen_manager(session, changes)

        manager.toggle_fullscreen()

        assert len(toggles) == 1
        assert session.fullscreen is case.expect_fullscreen
        assert session.set_calls[-1] is case.expect_fullscreen
        assert changes


class TestApplyFullscreenState:
    def test_enters_fullscreen_when_session_requests_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        toggles: List[int] = []
        monkeypatch.setattr(_TOGGLE_FULLSCREEN, lambda: toggles.append(1))
        session = FakeSession(fullscreen=True)
        manager = _fullscreen_manager(session, [])

        manager.apply_fullscreen_state()

        assert len(toggles) == 1
        assert session.fullscreen is True
        assert session.set_calls == []

    def test_stays_windowed_when_session_is_windowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        toggles: List[int] = []
        monkeypatch.setattr(_TOGGLE_FULLSCREEN, lambda: toggles.append(1))
        session = FakeSession(fullscreen=False)
        manager = _fullscreen_manager(session, [])

        manager.apply_fullscreen_state()

        assert toggles == []
