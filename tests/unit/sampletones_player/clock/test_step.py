from dataclasses import dataclass
from typing import Tuple

import pytest
from pydantic import ValidationError

from sampletones_player.clock.step import FixedPointStep
from sampletones_player.specification.clock import (
    FIXED_POINT_SCALE,
    MAX_STEP_FRACTION,
    MAX_STEP_WHOLE,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase


class TestFixedPointStep(BaseTestSuite):
    """The whole byte and the word the driver adds into its accumulator."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: int
        fields: Tuple[int, int]

        @property
        def label(self) -> str:
            whole, fraction = self.fields
            return f"{whole}-{fraction}"

    test_cases = (
        TestCase(fields=(0, 0), expected=0),
        TestCase(fields=(0, MAX_STEP_FRACTION), expected=MAX_STEP_FRACTION),
        TestCase(fields=(1, 0), expected=FIXED_POINT_SCALE),
        TestCase(fields=(3, 21837), expected=3 * FIXED_POINT_SCALE + 21837),
        TestCase(fields=(MAX_STEP_WHOLE, MAX_STEP_FRACTION), expected=FIXED_POINT_SCALE * (MAX_STEP_WHOLE + 1) - 1),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_value_composes_the_fields(self, test_case: TestCase) -> None:
        whole, fraction = test_case.fields
        assert FixedPointStep(whole=whole, fraction=fraction).value == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_fields_read_back_off_the_value(self, test_case: TestCase) -> None:
        whole, fraction = test_case.fields
        step = FixedPointStep(whole=whole, fraction=fraction)
        assert divmod(step.value, FIXED_POINT_SCALE) == (step.whole, step.fraction)

    @pytest.mark.parametrize("fraction", (-1, FIXED_POINT_SCALE))
    def test_a_fraction_outside_the_word_is_rejected(self, fraction: int) -> None:
        with pytest.raises(ValidationError):
            FixedPointStep(whole=0, fraction=fraction)

    @pytest.mark.parametrize("whole", (-1, MAX_STEP_WHOLE + 1))
    def test_a_whole_part_outside_the_byte_is_rejected(self, whole: int) -> None:
        with pytest.raises(ValidationError):
            FixedPointStep(whole=whole, fraction=0)
