from dataclasses import dataclass
from typing import Any, List, Type, Union

import numpy as np
import pytest

from sampletones_core.audio.mixing import align, common_length, mix
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestCommonLength:
    """The length a set of tracks reaches when they are laid over one another."""

    def test_the_longest_track_sets_the_length(self) -> None:
        assert common_length([np.zeros(3), np.zeros(7), np.zeros(5)]) == 7

    def test_tracks_of_one_length_keep_it(self) -> None:
        assert common_length([np.zeros(4), np.zeros(4)]) == 4

    def test_no_tracks_reach_no_length(self) -> None:
        assert common_length([]) == 0


class TestAlign(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[List[np.ndarray], Type[Exception]]
        tracks: Any
        length: int

    test_cases = (
        TestCase(
            label="a_shorter_track_runs_on_in_silence",
            tracks=[np.array([1.0, 2.0])],
            length=4,
            expected=[np.array([1.0, 2.0, 0.0, 0.0])],
        ),
        TestCase(
            label="a_longer_track_ends_at_the_length",
            tracks=[np.array([1.0, 2.0, 3.0])],
            length=2,
            expected=[np.array([1.0, 2.0])],
        ),
        TestCase(
            label="a_track_of_the_length_stands_as_it_is",
            tracks=[np.array([1.0, 2.0])],
            length=2,
            expected=[np.array([1.0, 2.0])],
        ),
        TestCase(
            label="every_track_reaches_the_same_length",
            tracks=[np.array([1.0]), np.array([2.0, 3.0, 4.0])],
            length=3,
            expected=[np.array([1.0, 0.0, 0.0]), np.array([2.0, 3.0, 4.0])],
        ),
        TestCase(
            label="no_tracks_align_to_none",
            tracks=[],
            length=5,
            expected=[],
        ),
        TestCase(
            label="a_negative_length_raises",
            tracks=[np.array([1.0])],
            length=-1,
            expected=ValueError,
        ),
        TestCase(
            label="a_two_dimensional_track_raises",
            tracks=[np.zeros((2, 2))],
            length=2,
            expected=ValueError,
        ),
        TestCase(
            label="a_list_is_not_a_track",
            tracks=[[1.0, 2.0]],
            length=2,
            expected=TypeError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_align(self, test_case: TestCase) -> None:
        if expect_error(align, test_case.expected, test_case.tracks, test_case.length):
            return

        aligned = align(test_case.tracks, test_case.length)
        assert len(aligned) == len(test_case.expected)
        for track, expected in zip(aligned, test_case.expected):
            assert_array_equal(track, expected)


class TestMix:
    """Tracks summed into one waveform, each carrying the level it reaches the mix at."""

    def test_tracks_of_one_length_sum_sample_by_sample(self) -> None:
        assert_array_equal(
            mix([np.array([0.25, -0.25]), np.array([0.5, 0.5])]),
            np.array([0.75, 0.25], dtype=np.float32),
        )

    def test_a_shorter_track_falls_silent_at_its_end(self) -> None:
        assert_array_equal(
            mix([np.array([1.0, 1.0, 1.0]), np.array([0.5])]),
            np.array([1.5, 1.0, 1.0], dtype=np.float32),
        )

    def test_the_mix_lasts_as_long_as_the_longest_track(self) -> None:
        assert len(mix([np.zeros(3), np.zeros(9)])) == 9

    def test_one_track_reaches_the_mix_as_it_stands(self) -> None:
        assert_array_equal(
            mix([np.array([0.5, -0.5])]),
            np.array([0.5, -0.5], dtype=np.float32),
        )

    def test_no_tracks_mix_to_silence(self) -> None:
        mixed = mix([])
        assert mixed.dtype == np.float32
        assert len(mixed) == 0

    def test_the_mix_is_float32_whatever_the_tracks_carry(self) -> None:
        assert mix([np.array([1, 2], dtype=np.int32)]).dtype == np.float32

    def test_a_track_that_is_not_an_array_raises(self) -> None:
        with pytest.raises(TypeError):
            mix([[1.0, 2.0]])
