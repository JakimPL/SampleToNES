from dataclasses import dataclass
from typing import Final, Sequence, Tuple

import numpy as np
import pytest

from sampletones_core.reconstructions.reconstructor.level import FrameReading, LevelReading, StandingFrame
from sampletones_core.reconstructions.reconstructor.level.line import (
    LEAST_STANDING_FRAMES,
    LEAST_STANDING_SHARE,
    MOST_SPREAD,
    READING_WIDTH,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

LEVEL: Final[float] = 0.6
OTHER_LEVEL: Final[float] = 0.9
NOTE: Final[int] = 48
STEM: Final[int] = 0
OTHER_STEM: Final[int] = 1
STRAYS: Final[Tuple[float, ...]] = (0.66, 0.70, 0.74, 0.78, 0.82)
SPREAD_MARGIN: Final[float] = 1e-6


def _reading(levels: Sequence[float], sampled: int, stem_id: int = STEM) -> LevelReading:
    standing = tuple(
        StandingFrame(stem_id=stem_id, index=index, reading=FrameReading(level=level, note=NOTE))
        for index, level in enumerate(levels)
    )
    return LevelReading(sampled=sampled, standing=standing)


class TestTheLevelTheFramesAgreeOn:
    def test_frames_agreeing_on_a_triangle_line_give_its_level(self) -> None:
        frames = 2 * LEAST_STANDING_FRAMES

        assert _reading((LEVEL,) * frames, frames).level == pytest.approx(LEVEL)

    def test_a_bass_reading_quieter_or_louder_on_some_frames_is_read_where_the_most_frames_agree(self) -> None:
        frames = 4 * LEAST_STANDING_FRAMES
        strays = {0: 0.85, 1: 1.15}
        levels = tuple(LEVEL * strays.get(index % 4, 1.0) for index in range(frames))

        assert _reading(levels, frames).level == pytest.approx(LEVEL)

    def test_the_level_is_where_the_readings_gather_and_not_their_median(self) -> None:
        """The strays come first, so a reading picked by its order or by the median lands on a stray."""
        levels = (*STRAYS, *(LEVEL,) * LEAST_STANDING_FRAMES)
        reading = _reading(levels, len(levels))

        assert float(np.median(levels)) != pytest.approx(LEVEL)
        assert reading.level == LEVEL

    def test_readings_scattered_wider_than_the_spread_allowed_give_no_level(self) -> None:
        frames = 2 * LEAST_STANDING_FRAMES
        wide = 2.0 * MOST_SPREAD
        levels = tuple(LEVEL * (1.0 + wide * (index % 2 - 0.5)) for index in range(frames))

        assert _reading(levels, frames).level is None


class TestWhetherALineStands(BaseTestSuite):
    """A line stands on enough frames: at least a share of those read, and a least count however few were read."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        standing: int
        sampled: int
        expected: bool

    test_cases = (
        TestCase(label="a_single_frame_read_and_standing", standing=1, sampled=1, expected=False),
        TestCase(
            label="one_frame_short_of_the_least",
            standing=LEAST_STANDING_FRAMES - 1,
            sampled=LEAST_STANDING_FRAMES - 1,
            expected=False,
        ),
        TestCase(
            label="the_least_count_every_frame",
            standing=LEAST_STANDING_FRAMES,
            sampled=LEAST_STANDING_FRAMES,
            expected=True,
        ),
        TestCase(
            label="exactly_the_share_of_the_frames_read",
            standing=LEAST_STANDING_FRAMES,
            sampled=int(LEAST_STANDING_FRAMES / LEAST_STANDING_SHARE),
            expected=True,
        ),
        TestCase(
            label="one_frame_read_beyond_the_share",
            standing=LEAST_STANDING_FRAMES,
            sampled=int(LEAST_STANDING_FRAMES / LEAST_STANDING_SHARE) + 1,
            expected=False,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_line_stands_on_enough_of_the_frames_read(self, test_case: TestCase) -> None:
        reading = _reading((LEVEL,) * test_case.standing, test_case.sampled)

        assert reading.stands is test_case.expected
        assert (reading.level is not None) is test_case.expected

    def test_no_frame_read_stands_no_line(self) -> None:
        assert _reading((), 0).level is None


def _quartiles_apart(spread: float) -> Tuple[float, ...]:
    """Readings around a median of one whose quartiles lie ``spread`` apart."""
    return (1.0 - spread / 2, 1.0 - spread / 2, 1.0 + spread / 2, 1.0 + spread / 2)


class TestWhetherTheReadingsAgree(BaseTestSuite):
    """Readings agree where their quartiles lie at most the spread allowed of their median apart."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        spread: float
        expected: bool

    test_cases = (
        TestCase(label="just_within_the_spread", spread=MOST_SPREAD * (1.0 - SPREAD_MARGIN), expected=True),
        TestCase(label="just_beyond_the_spread", spread=MOST_SPREAD * (1.0 + SPREAD_MARGIN), expected=False),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_readings_agree_up_to_the_spread_allowed(self, test_case: TestCase) -> None:
        levels = _quartiles_apart(test_case.spread)

        assert _reading(levels, len(levels)).agrees is test_case.expected

    def test_readings_reaching_far_beyond_their_quartiles_agree_on_the_quartiles(self) -> None:
        levels = (LEVEL / 10, *(LEVEL,) * LEAST_STANDING_FRAMES, LEVEL * 10)

        assert _reading(levels, len(levels)).agrees

    def test_readings_of_no_loudness_disagree(self) -> None:
        assert not _reading((0.0,) * LEAST_STANDING_FRAMES, LEAST_STANDING_FRAMES).agrees


class TestTheDensestReading:
    def test_of_two_groups_alike_the_one_standing_first_gives_the_level(self) -> None:
        levels = (LEVEL, OTHER_LEVEL) * LEAST_STANDING_FRAMES

        assert _reading(levels, len(levels)).densest == LEVEL
        assert _reading(levels[::-1], len(levels)).densest == OTHER_LEVEL

    def test_readings_within_the_width_lie_near_one_another(self) -> None:
        """Two readings a tenth of the width apart outweigh three standing many widths apart, and first."""
        near = LEVEL * float(np.exp(0.1 * READING_WIDTH))
        far = tuple(LEVEL * float(np.exp(widths * READING_WIDTH)) for widths in (-20, 20, 40))
        levels = (*far, near, LEVEL)

        assert _reading(levels, len(levels)).densest in (near, LEVEL)


class TestPoolingStems:
    def test_the_stems_readings_are_read_together_in_the_order_given(self) -> None:
        first = _reading((LEVEL,) * 2, 3, STEM)
        second = _reading((OTHER_LEVEL,) * 3, 5, OTHER_STEM)

        pooled = LevelReading.pooled([first, second])

        assert pooled.sampled == 8
        assert pooled.standing == (*first.standing, *second.standing)


class TestTheSampleJudged:
    def test_a_sample_wider_than_the_frames_holds_every_frame(self) -> None:
        reading = _reading((LEVEL,) * LEAST_STANDING_FRAMES, LEAST_STANDING_FRAMES)

        assert reading.sample(LEAST_STANDING_FRAMES) == list(reading.standing)
        assert reading.sample(LEAST_STANDING_FRAMES + 1) == list(reading.standing)

    def test_a_sample_spreads_evenly_from_the_first_frame_to_the_last(self) -> None:
        reading = _reading((LEVEL,) * 10, 10)

        assert [frame.index for frame in reading.sample(4)] == [0, 3, 6, 9]

    def test_a_sample_of_one_frame_is_the_first(self) -> None:
        reading = _reading((LEVEL,) * 5, 5)

        assert [frame.index for frame in reading.sample(1)] == [0]
