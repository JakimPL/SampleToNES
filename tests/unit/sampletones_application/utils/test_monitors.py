from typing import List

import pytest
from screeninfo import Monitor, ScreenInfoError

from sampletones_application.utils.monitors import (
    MonitorArea,
    available_monitors,
    monitor_area_for_window,
    monitor_for_window,
)
from sampletones_shared.display import Resolution

GET_MONITORS = "sampletones_application.utils.monitors.get_monitors"

PRIMARY = Monitor(x=0, y=0, width=1920, height=1080)
SECONDARY = Monitor(x=1920, y=0, width=2560, height=1440)

USABLE_RATIO = 0.9
FALLBACK_MONITOR = Resolution(width=1920, height=1080)


def area_for_window(x: int, y: int, width: int, height: int) -> MonitorArea:
    return monitor_area_for_window(
        x,
        y,
        width,
        height,
        usable_ratio=USABLE_RATIO,
        fallback_monitor=FALLBACK_MONITOR,
    )


class TestAvailableMonitors:
    def test_the_platform_listing_is_passed_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, lambda: [PRIMARY, SECONDARY])

        assert available_monitors() == [PRIMARY, SECONDARY]

    def test_a_platform_without_an_enumerator_reports_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A headless session makes screeninfo raise, which stays recoverable."""

        def raise_screen_info_error() -> List[Monitor]:
            raise ScreenInfoError("No enumerators available")

        monkeypatch.setattr(GET_MONITORS, raise_screen_info_error)

        assert available_monitors() == []


class TestMonitorForWindow:
    def test_the_monitor_holding_the_window_is_chosen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, lambda: [PRIMARY, SECONDARY])

        assert monitor_for_window(2000, 100, 1280, 800) is SECONDARY

    def test_a_window_spanning_two_monitors_takes_the_one_it_covers_most(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(GET_MONITORS, lambda: [PRIMARY, SECONDARY])

        assert monitor_for_window(1820, 100, 1280, 800) is SECONDARY

    def test_a_window_away_from_every_monitor_takes_the_first(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, lambda: [PRIMARY, SECONDARY])

        assert monitor_for_window(-5000, -5000, 1280, 800) is PRIMARY

    def test_nothing_is_chosen_where_none_is_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, list)

        assert monitor_for_window(0, 0, 1280, 800) is None


class TestMonitorArea:
    def test_the_usable_size_leaves_the_decoration_frame_room(self) -> None:
        area = MonitorArea.of(PRIMARY, USABLE_RATIO)

        assert area.usable_width == int(PRIMARY.width * USABLE_RATIO)
        assert area.usable_height == int(PRIMARY.height * USABLE_RATIO)

    def test_the_area_carries_the_monitor_origin(self) -> None:
        area = MonitorArea.of(SECONDARY, USABLE_RATIO)

        assert (area.x, area.y) == (SECONDARY.x, SECONDARY.y)

    def test_an_assumed_area_takes_the_given_size_at_the_origin(self) -> None:
        assert MonitorArea.assumed(FALLBACK_MONITOR, USABLE_RATIO) == MonitorArea(
            x=0,
            y=0,
            width=FALLBACK_MONITOR.width,
            height=FALLBACK_MONITOR.height,
            usable_ratio=USABLE_RATIO,
        )

    def test_a_window_falls_back_to_the_assumed_area(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, list)

        assert area_for_window(0, 0, 1280, 800) == MonitorArea.assumed(FALLBACK_MONITOR, USABLE_RATIO)

    def test_a_window_takes_the_area_of_the_monitor_it_sits_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(GET_MONITORS, lambda: [PRIMARY, SECONDARY])

        assert area_for_window(2000, 100, 1280, 800) == MonitorArea.of(SECONDARY, USABLE_RATIO)


class TestMonitorAreaValidation:
    @pytest.mark.parametrize("usable_ratio", [0.0, -0.5, 1.5])
    def test_a_ratio_outside_the_monitor_raises(self, usable_ratio: float) -> None:
        """A window takes a positive share of its monitor, at most the whole of it."""
        with pytest.raises(ValueError):
            MonitorArea(x=0, y=0, width=1920, height=1080, usable_ratio=usable_ratio)

    @pytest.mark.parametrize(("width", "height"), [(0, 1080), (1920, 0), (-1920, -1080)])
    def test_an_area_without_extent_raises(self, width: int, height: int) -> None:
        with pytest.raises(ValueError):
            MonitorArea(x=0, y=0, width=width, height=height, usable_ratio=USABLE_RATIO)
