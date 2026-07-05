from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Final, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.calibration.config import RefereeConfig, load_referee_config

VALID_FIELDS: Final[Dict[str, Any]] = {
    "window_sizes": (512, 2048),
    "hop_divisor": 4,
    "band_count": 40,
    "low_frequency": 30.0,
    "energy_floor": 1e-10,
    "audibility_range_decibels": 60.0,
}


@dataclass(frozen=True)
class InvalidFieldCase:
    name: str
    field: str
    value: Any


INVALID_FIELD_CASES: Final[Tuple[InvalidFieldCase, ...]] = (
    InvalidFieldCase(name="empty_window_sizes", field="window_sizes", value=()),
    InvalidFieldCase(name="nonpositive_window_size", field="window_sizes", value=(512, 0)),
    InvalidFieldCase(name="zero_hop_divisor", field="hop_divisor", value=0),
    InvalidFieldCase(name="zero_band_count", field="band_count", value=0),
    InvalidFieldCase(name="zero_low_frequency", field="low_frequency", value=0.0),
    InvalidFieldCase(name="zero_energy_floor", field="energy_floor", value=0.0),
    InvalidFieldCase(name="zero_audibility_range", field="audibility_range_decibels", value=0.0),
)


class TestRefereeConfig:
    def test_packaged_configuration_loads(self) -> None:
        config = load_referee_config()
        assert isinstance(config, RefereeConfig)

    @pytest.mark.parametrize("case", INVALID_FIELD_CASES, ids=lambda case: case.name)
    def test_out_of_bounds_field_is_rejected(self, case: InvalidFieldCase) -> None:
        fields = {**VALID_FIELDS, case.field: case.value}
        with pytest.raises(ValidationError):
            RefereeConfig.model_validate(fields)
