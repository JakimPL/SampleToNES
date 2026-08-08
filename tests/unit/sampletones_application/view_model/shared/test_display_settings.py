from typing import Tuple

import pytest

from sampletones_application.view_model.shared.display_settings import (
    available_resolutions,
    frame_rate_label,
    frame_rate_labels,
    nearest_frame_rate,
    nearest_resolution,
    resolution_labels,
)
from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution

UNLIMITED_LABEL = "Unlimited"

DESKTOP_BOUND = (1728, 972)
LAPTOP_BOUND = (1229, 691)
WIDE_BOUND = (3456, 1944)

MIN_WIDTH = 1024
MIN_HEIGHT = 640

RESOLUTIONS: Tuple[Resolution, ...] = (
    Resolution(width=1024, height=768),
    Resolution(width=1152, height=648),
    Resolution(width=1280, height=800),
    Resolution(width=1600, height=900),
    Resolution(width=1920, height=1080),
    Resolution(width=2560, height=1440),
    Resolution(width=3840, height=2160),
)

FRAME_RATES: Tuple[int, ...] = (UNLIMITED_FRAME_RATE, 30, 60, 90, 120, 240)


def offered(
    bound: Tuple[int, int],
    *,
    min_width: int = MIN_WIDTH,
    min_height: int = MIN_HEIGHT,
) -> Tuple[Resolution, ...]:
    max_width, max_height = bound
    return available_resolutions(
        RESOLUTIONS,
        min_width=min_width,
        min_height=min_height,
        max_width=max_width,
        max_height=max_height,
    )


class TestAvailableResolutions:
    def test_every_offered_size_stays_within_the_bounds(self) -> None:
        assert all(resolution.fits_within(*DESKTOP_BOUND) for resolution in offered(DESKTOP_BOUND))

    def test_every_offered_size_meets_the_window_minimum(self) -> None:
        resolutions = offered(WIDE_BOUND, min_width=1600, min_height=900)

        assert all(resolution.reaches(1600, 900) for resolution in resolutions)

    def test_a_size_beyond_the_bounds_is_left_to_fullscreen(self) -> None:
        """A window is held below the monitor so its frame stays on screen."""
        assert Resolution(width=1920, height=1080) not in offered(DESKTOP_BOUND)

    def test_a_larger_bound_offers_more(self) -> None:
        assert set(offered(DESKTOP_BOUND)) < set(offered(WIDE_BOUND))

    def test_a_small_laptop_is_offered_a_size_of_its_own(self) -> None:
        """A screen with room for few sizes still picks from the offered list."""
        assert set(offered(LAPTOP_BOUND)) <= set(RESOLUTIONS)

    def test_the_offered_sizes_keep_the_order_they_are_given_in(self) -> None:
        resolutions = offered(WIDE_BOUND)

        assert list(resolutions) == [resolution for resolution in RESOLUTIONS if resolution in resolutions]

    def test_bounds_with_room_for_none_offer_the_window_minimum(self) -> None:
        assert offered((800, 600)) == (Resolution(width=MIN_WIDTH, height=MIN_HEIGHT),)

    def test_a_label_spells_the_size(self) -> None:
        assert resolution_labels((Resolution(width=1280, height=800),)) == ("1280x800",)


class TestFrameRates:
    def test_the_unlimited_setting_is_offered_by_name(self) -> None:
        assert frame_rate_label(UNLIMITED_FRAME_RATE, unlimited_label=UNLIMITED_LABEL) == UNLIMITED_LABEL

    def test_a_capped_rate_is_offered_by_number(self) -> None:
        assert frame_rate_label(60, unlimited_label=UNLIMITED_LABEL) == "60"

    def test_every_offered_rate_carries_a_label(self) -> None:
        labels = frame_rate_labels(FRAME_RATES, unlimited_label=UNLIMITED_LABEL)

        assert len(labels) == len(FRAME_RATES)

    def test_a_stored_rate_that_is_offered_selects_itself(self) -> None:
        assert nearest_frame_rate(60, FRAME_RATES) == 60

    def test_a_stored_rate_the_build_stopped_offering_selects_the_closest(self) -> None:
        """A preference outlives the list offered when it was written."""
        assert nearest_frame_rate(100, FRAME_RATES) == 90

    def test_a_rate_beyond_the_offered_ones_selects_the_highest(self) -> None:
        assert nearest_frame_rate(1000, FRAME_RATES) == max(FRAME_RATES)

    def test_selecting_without_an_offered_rate_raises(self) -> None:
        with pytest.raises(ValueError):
            nearest_frame_rate(60, ())


class TestNearestResolution:
    def test_a_window_at_an_offered_size_selects_it(self) -> None:
        assert nearest_resolution(1280, 800, offered(DESKTOP_BOUND)) == Resolution(width=1280, height=800)

    def test_a_window_between_two_sizes_selects_the_closer(self) -> None:
        assert nearest_resolution(1290, 810, offered(WIDE_BOUND)) == Resolution(width=1280, height=800)

    def test_selecting_without_an_offered_size_raises(self) -> None:
        with pytest.raises(ValueError):
            nearest_resolution(1280, 800, ())
