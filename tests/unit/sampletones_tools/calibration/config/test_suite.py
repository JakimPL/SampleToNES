from dataclasses import dataclass
from typing import Any, Dict, Final

import pytest
from pydantic import ValidationError

from sampletones_tools.calibration.config.suite import SuiteConfig
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

VALID_FIELDS: Final[Dict[str, Any]] = {
    "methods": ("fft", "cqt"),
    "perceptual_exponents": (1.0,),
    "temporal_weights": (),
    "channels": ("pulse1", "triangle"),
}


class TestSuiteConfig(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        field: str
        value: Any

    test_cases = (
        TestCase(field="methods", value=(), label="no_methods"),
        TestCase(field="methods", value=("dct",), label="unknown_method"),
        TestCase(field="perceptual_exponents", value=(), label="no_exponents"),
        TestCase(field="perceptual_exponents", value=(-0.5,), label="negative_exponent"),
        TestCase(field="temporal_weights", value=(1.5,), label="temporal_weight_above_one"),
        TestCase(field="channels", value=(), label="no_channels"),
        TestCase(field="channels", value=("dpcm",), label="unknown_channel"),
    )

    def test_packaged_suite_loads(self) -> None:
        assert isinstance(SuiteConfig.load(), SuiteConfig)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_out_of_bounds_field_is_rejected(self, test_case: TestCase) -> None:
        with pytest.raises(ValidationError):
            SuiteConfig.model_validate({**VALID_FIELDS, test_case.field: test_case.value})

    @pytest.mark.parametrize("field", sorted(VALID_FIELDS))
    def test_missing_field_is_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError):
            SuiteConfig.model_validate({key: value for key, value in VALID_FIELDS.items() if key != field})
