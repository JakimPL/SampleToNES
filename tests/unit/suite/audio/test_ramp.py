from dataclasses import dataclass

import numpy as np
import pytest

from tests.suite.audio.ramp import RAMP_STEP, ramp, ramp_indices
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


class TestRamp(BaseTestSuite):
    """Ramp audio states each sample's document index, and reads back to exactly those indices."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        frames: int
        start: int

    test_cases = (
        TestCase(frames=8, start=0, label="from_the_beginning"),
        TestCase(frames=8, start=500, label="from_a_later_index"),
        TestCase(frames=4, start=2**20 - 4, label="up_to_a_million_samples"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_samples_read_back_to_their_indices(self, test_case: TestCase) -> None:
        samples = ramp(test_case.frames, start=test_case.start)

        np.testing.assert_array_equal(
            ramp_indices(samples),
            np.arange(test_case.start, test_case.start + test_case.frames),
        )

    def test_every_sample_stays_below_full_scale(self) -> None:
        assert float(ramp(4, start=2**20 - 4).max()) < 1.0

    def test_a_value_between_two_indices_reads_as_the_nearer_one(self) -> None:
        between = np.array([3.4 * RAMP_STEP, 3.6 * RAMP_STEP], dtype=np.float32)

        np.testing.assert_array_equal(ramp_indices(between), [3, 4])
