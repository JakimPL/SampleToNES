from typing import Tuple

import pytest

from sampletones_application.view_model.shared.display_settings import (
    DisplaySettings,
    DisplaySettingsViewModel,
    WindowMode,
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


PALETTES: Tuple[str, ...] = ("dark", "light", "studio")


def settings(
    *,
    resolution: Resolution = Resolution(width=1280, height=800),
    borderless: bool = False,
    fullscreen: bool = False,
    frame_rate: int = 60,
) -> DisplaySettings:
    return DisplaySettings(
        palette="studio",
        window=WindowMode(
            resolution=resolution,
            borderless=borderless,
            fullscreen=fullscreen,
        ),
        vsync=True,
        frame_rate=frame_rate,
    )


def view_model(
    display_settings: DisplaySettings,
    bound: Tuple[int, int] = WIDE_BOUND,
) -> DisplaySettingsViewModel:
    max_width, max_height = bound
    return DisplaySettingsViewModel.build(
        display_settings,
        resolutions=RESOLUTIONS,
        frame_rates=FRAME_RATES,
        palettes=PALETTES,
        min_width=MIN_WIDTH,
        min_height=MIN_HEIGHT,
        max_width=max_width,
        max_height=max_height,
    )


class TestSettingsChanges:
    def test_changing_one_entry_leaves_the_rest_standing(self) -> None:
        changed = settings().with_palette("dark")

        assert changed.palette == "dark"
        assert changed.window == settings().window

    def test_changing_one_part_of_the_window_mode_leaves_the_rest_standing(
        self,
    ) -> None:
        window = settings().window.with_borderless(True)

        assert window.borderless is True
        assert window.resolution == Resolution(width=1280, height=800)

    def test_the_settings_a_change_was_asked_of_stay_as_they_were(self) -> None:
        """A snapshot taken before an edit still reads the state it was taken from."""
        snapshot = settings()
        snapshot.with_vsync(False)

        assert snapshot.vsync is True


class TestDisplaySettingsViewModel:
    def test_the_offer_holds_only_what_the_monitor_leaves_room_for(self) -> None:
        assert view_model(settings(), DESKTOP_BOUND).resolutions == offered(DESKTOP_BOUND)

    def test_a_window_at_a_size_of_its_own_selects_the_nearest_offered_one(
        self,
    ) -> None:
        built = view_model(settings(resolution=Resolution(width=1290, height=810)))

        assert built.settings.window.resolution == Resolution(width=1280, height=800)

    def test_a_stored_rate_the_build_stopped_offering_selects_the_closest(self) -> None:
        assert view_model(settings(frame_rate=100)).settings.frame_rate == 90

    def test_a_windowed_window_offers_its_size_and_frame(self) -> None:
        assert view_model(settings()).window_controls_enabled

    def test_a_fullscreen_window_offers_neither_a_size_nor_a_frame(self) -> None:
        assert not view_model(settings(fullscreen=True)).window_controls_enabled

    def test_every_offered_size_carries_an_item(self) -> None:
        built = view_model(settings())

        assert len(built.resolution_items) == len(built.resolutions)

    def test_the_selected_size_reads_as_one_of_the_offered_items(self) -> None:
        built = view_model(settings())

        assert built.current_resolution_item in built.resolution_items

    def test_the_selected_rate_reads_as_one_of_the_offered_items(self) -> None:
        built = view_model(settings())

        assert built.current_frame_rate_item(UNLIMITED_LABEL) in built.frame_rate_items(UNLIMITED_LABEL)

    def test_an_item_leads_back_to_the_size_it_stands_for(self) -> None:
        built = view_model(settings())

        assert built.resolution_for_item("1600x900") == Resolution(width=1600, height=900)

    def test_an_item_leads_back_to_the_rate_it_stands_for(self) -> None:
        built = view_model(settings())

        assert built.frame_rate_for_item(UNLIMITED_LABEL, UNLIMITED_LABEL) == UNLIMITED_FRAME_RATE

    def test_an_item_no_size_carries_raises(self) -> None:
        with pytest.raises(KeyError):
            view_model(settings()).resolution_for_item("640x480")

    def test_an_item_no_rate_carries_raises(self) -> None:
        with pytest.raises(KeyError):
            view_model(settings()).frame_rate_for_item("360", UNLIMITED_LABEL)
