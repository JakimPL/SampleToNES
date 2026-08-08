from typing import Any, Dict, List

import pytest
from pydantic import ValidationError

from sampletones_application.config.session.application.display import DEFAULT_MAX_FPS
from sampletones_application.layout.behavior.behavior import BehaviorConfig
from sampletones_application.layout.behavior.display import DisplayBehavior
from sampletones_application.paths import BEHAVIOR_DIRECTORY
from sampletones_shared.display import UNLIMITED_FRAME_RATE, Resolution
from sampletones_shared.utils.serialization import load_yaml_model

RESOLUTIONS: List[Dict[str, int]] = [
    {"width": 1024, "height": 768},
    {"width": 1280, "height": 720},
    {"width": 1280, "height": 800},
]

FRAME_RATES: List[int] = [UNLIMITED_FRAME_RATE, 30, 60]

COUNTDOWN_SECONDS: float = 10.0


def behavior(**overrides: Any) -> DisplayBehavior:
    return DisplayBehavior.model_validate(
        {
            "resolutions": RESOLUTIONS,
            "frame_rates": FRAME_RATES,
            "revert_countdown_seconds": COUNTDOWN_SECONDS,
            **overrides,
        }
    )


class TestDisplayBehavior:
    def test_the_offered_sizes_are_read_as_resolutions(self) -> None:
        assert behavior().resolutions[0] == Resolution(width=1024, height=768)

    @pytest.mark.parametrize(
        "resolutions",
        [
            [{"width": 1280, "height": 800}, {"width": 1024, "height": 768}],
            [{"width": 1280, "height": 800}, {"width": 1280, "height": 720}],
            [{"width": 1024, "height": 768}, {"width": 1024, "height": 768}],
        ],
        ids=["descending", "same_width_descending_height", "repeated"],
    )
    def test_sizes_out_of_ascending_order_raise(self, resolutions: List[Dict[str, int]]) -> None:
        """A combo shows the file's order, so the order it declares is the order it is read in."""
        with pytest.raises(ValidationError):
            behavior(resolutions=resolutions)

    @pytest.mark.parametrize(
        "frame_rates",
        [[60, 30], [30, 30]],
        ids=["descending", "repeated"],
    )
    def test_rates_out_of_ascending_order_raise(self, frame_rates: List[int]) -> None:
        with pytest.raises(ValidationError):
            behavior(frame_rates=frame_rates)

    @pytest.mark.parametrize("field", ["resolutions", "frame_rates"])
    def test_an_empty_list_raises(self, field: str) -> None:
        """A combo offers at least one entry to select."""
        with pytest.raises(ValidationError):
            behavior(**{field: []})

    def test_a_size_without_extent_raises(self) -> None:
        with pytest.raises(ValidationError):
            behavior(resolutions=[{"width": 0, "height": 768}])

    @pytest.mark.parametrize("seconds", [0.0, -1.0])
    def test_a_countdown_without_time_raises(self, seconds: float) -> None:
        """A window mode nobody confirms is given time to be judged in."""
        with pytest.raises(ValidationError):
            behavior(revert_countdown_seconds=seconds)


@pytest.fixture(scope="module")
def display() -> DisplayBehavior:
    return load_yaml_model(BEHAVIOR_DIRECTORY / "general.yaml", BehaviorConfig).display


class TestShippedDisplayBehavior:
    def test_the_shipped_catalog_loads(self, display: DisplayBehavior) -> None:
        assert display.resolutions and display.frame_rates

    def test_the_unlimited_setting_is_offered(self, display: DisplayBehavior) -> None:
        assert UNLIMITED_FRAME_RATE in display.frame_rates

    def test_the_default_frame_rate_is_one_of_the_offered_rates(self, display: DisplayBehavior) -> None:
        assert DEFAULT_MAX_FPS in display.frame_rates

    def test_a_window_mode_is_given_time_to_be_judged_in(self, display: DisplayBehavior) -> None:
        assert display.revert_countdown_seconds > 0.0
