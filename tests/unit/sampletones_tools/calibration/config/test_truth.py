import pytest

from sampletones_tools.calibration.config.truth import TruthConfig


class TestTruthConfig:
    def test_the_packaged_settings_read(self) -> None:
        assert TruthConfig.load().audible_decibels > 0.0

    def test_the_audible_floor_is_the_level_the_threshold_stands_for(self) -> None:
        assert TruthConfig(audible_decibels=20.0).audible_floor == pytest.approx(0.1)
