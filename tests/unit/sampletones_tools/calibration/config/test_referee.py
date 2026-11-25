from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.referee import RefereeConfig
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

VALID_FIELDS: Final[Dict[str, Any]] = {
    "window_sizes": (512, 2048),
    "hop_divisor": 4,
    "band_count": 40,
    "low_frequency": 30.0,
    "energy_floor": 1e-10,
    "audibility_range_decibels": 60.0,
    "compression_exponent": 0.3,
    "dynamic_range_decibels": 60.0,
    "level_matching": True,
    "contour_frame_rate": 60,
    "contour_audible_decibels": 40.0,
    "contour_onset_frames": 3,
    "contour_band_centers": (125.0, 1000.0),
    "contour_band_floor_decibels": 60.0,
    "volume_tolerance": 1,
    "misplaced_weight": 0.75,
}


class TestRefereeConfig(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        field: str
        value: Any

    test_cases = (
        TestCase(
            field="window_sizes",
            value=(),
            label="empty_window_sizes",
        ),
        TestCase(
            field="window_sizes",
            value=(512, 0),
            label="nonpositive_window_size",
        ),
        TestCase(
            field="hop_divisor",
            value=0,
            label="zero_hop_divisor",
        ),
        TestCase(
            field="band_count",
            value=0,
            label="zero_band_count",
        ),
        TestCase(
            field="low_frequency",
            value=0.0,
            label="zero_low_frequency",
        ),
        TestCase(
            field="energy_floor",
            value=0.0,
            label="zero_energy_floor",
        ),
        TestCase(
            field="audibility_range_decibels",
            value=0.0,
            label="zero_audibility_range",
        ),
        TestCase(
            field="compression_exponent",
            value=0.0,
            label="zero_compression_exponent",
        ),
        TestCase(
            field="compression_exponent",
            value=1.5,
            label="expanding_compression_exponent",
        ),
        TestCase(
            field="dynamic_range_decibels",
            value=0.0,
            label="zero_dynamic_range",
        ),
        TestCase(
            field="volume_tolerance",
            value=-1,
            label="negative_volume_tolerance",
        ),
        TestCase(
            field="contour_frame_rate",
            value=0,
            label="zero_contour_frame_rate",
        ),
        TestCase(
            field="contour_audible_decibels",
            value=0.0,
            label="zero_contour_audible_range",
        ),
        TestCase(
            field="contour_onset_frames",
            value=0,
            label="zero_contour_onset_frames",
        ),
        TestCase(
            field="contour_band_centers",
            value=(),
            label="no_contour_bands",
        ),
        TestCase(
            field="contour_band_floor_decibels",
            value=0.0,
            label="zero_contour_band_floor",
        ),
        TestCase(
            field="misplaced_weight",
            value=1.5,
            label="misplaced_note_outweighing_a_wrong_one",
        ),
        TestCase(
            field="misplaced_weight",
            value=-0.25,
            label="negative_misplaced_weight",
        ),
    )

    def test_packaged_configuration_loads(self) -> None:
        config = RefereeConfig.load()
        assert isinstance(config, RefereeConfig)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_out_of_bounds_field_is_rejected(self, test_case: TestCase) -> None:
        fields = {**VALID_FIELDS, test_case.field: test_case.value}
        with pytest.raises(ValidationError):
            RefereeConfig.model_validate(fields)

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_missing_field_is_rejected(self, field: str) -> None:
        fields = {key: value for key, value in VALID_FIELDS.items() if key != field}
        with pytest.raises(ValidationError):
            RefereeConfig.model_validate(fields)
