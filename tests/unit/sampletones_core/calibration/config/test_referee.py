from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_core.calibration.config.referee import RefereeConfig
from tests.suite.case import BaseRegularTestCase

VALID_FIELDS: Final[Dict[str, Any]] = {
    "window_sizes": (512, 2048),
    "hop_divisor": 4,
    "band_count": 40,
    "low_frequency": 30.0,
    "energy_floor": 1e-10,
    "audibility_range_decibels": 60.0,
}


class TestRefereeConfig:
    @dataclass(frozen=True, kw_only=True)
    class InvalidFieldCase(BaseRegularTestCase):
        field: str
        value: Any

    test_cases = (
        InvalidFieldCase(
            field="window_sizes",
            value=(),
            label="empty_window_sizes",
        ),
        InvalidFieldCase(
            field="window_sizes",
            value=(512, 0),
            label="nonpositive_window_size",
        ),
        InvalidFieldCase(
            field="hop_divisor",
            value=0,
            label="zero_hop_divisor",
        ),
        InvalidFieldCase(
            field="band_count",
            value=0,
            label="zero_band_count",
        ),
        InvalidFieldCase(
            field="low_frequency",
            value=0.0,
            label="zero_low_frequency",
        ),
        InvalidFieldCase(
            field="energy_floor",
            value=0.0,
            label="zero_energy_floor",
        ),
        InvalidFieldCase(
            field="audibility_range_decibels",
            value=0.0,
            label="zero_audibility_range",
        ),
    )

    def test_packaged_configuration_loads(self) -> None:
        config = RefereeConfig.load()
        assert isinstance(config, RefereeConfig)

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_out_of_bounds_field_is_rejected(self, case: InvalidFieldCase) -> None:
        fields = {**VALID_FIELDS, case.field: case.value}
        with pytest.raises(ValidationError):
            RefereeConfig.model_validate(fields)

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_missing_field_is_rejected(self, field: str) -> None:
        fields = {key: value for key, value in VALID_FIELDS.items() if key != field}
        with pytest.raises(ValidationError):
            RefereeConfig.model_validate(fields)
