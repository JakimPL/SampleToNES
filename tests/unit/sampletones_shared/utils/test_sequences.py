from dataclasses import dataclass
from typing import Final, Sequence

import numpy as np
import pytest

from sampletones_shared.utils.sequences import hold
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

STREAM: Final[bytes] = bytes((12, 5, 7))


class TestHold(BaseTestSuite):
    """A held stream reads as stated over the positions it covers and as its final value past them."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        values: Sequence[int]
        index: int
        expected: int

    test_cases = (
        TestCase(label="first_position", values=STREAM, index=0, expected=12),
        TestCase(label="middle_position", values=STREAM, index=1, expected=5),
        TestCase(label="final_position", values=STREAM, index=2, expected=7),
        TestCase(label="one_past_the_end_holds_the_final_value", values=STREAM, index=3, expected=7),
        TestCase(label="far_past_the_end_holds_the_final_value", values=STREAM, index=10_000, expected=7),
        TestCase(label="a_single_value_holds_everywhere", values=(4,), index=9, expected=4),
        TestCase(label="a_tuple_reads_alike", values=(1, 2, 3), index=5, expected=3),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_value_read(self, test_case: TestCase) -> None:
        assert hold(test_case.values, test_case.index) == test_case.expected

    def test_an_array_reads_its_elements(self) -> None:
        assert int(hold(np.array([0.5, 0.25]), 3) * 4) == 1

    @pytest.mark.parametrize("values", [b"", (), []], ids=["bytes", "tuple", "list"])
    def test_an_empty_stream_holds_nothing_to_read(self, values: Sequence[int]) -> None:
        with pytest.raises(ValueError):
            hold(values, 0)

    @pytest.mark.parametrize("index", [-1, -len(STREAM), -len(STREAM) - 1])
    def test_a_negative_index_is_refused_rather_than_read_from_the_end(self, index: int) -> None:
        with pytest.raises(ValueError):
            hold(STREAM, index)
