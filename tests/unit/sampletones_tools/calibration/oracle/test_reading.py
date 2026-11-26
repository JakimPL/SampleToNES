from typing import Dict, Final, Tuple

import pytest

from sampletones_tools.calibration.oracle.reading import HIGHEST_READING, LOWEST_READING, OracleReading
from sampletones_tools.calibration.referee.protocol import SCORE_READING, Judgment
from tests.suite.base import BaseTestSuite

HEADLINE: Final[str] = "mr-auditory-dB"
SECOND: Final[str] = "mr-loudness-dB"
PART: Final[str] = "missing"
SCORES: Final[Tuple[float, ...]] = (1.0, 4.0, 2.0, 3.5)


def _start(score: float) -> Dict[str, Judgment]:
    return {
        HEADLINE: Judgment(score=score, components={PART: 2.0 * score}),
        SECOND: Judgment(score=10.0 - score, components={}),
    }


@pytest.fixture(name="reading")
def reading_fixture() -> OracleReading:
    return OracleReading(starts=tuple(_start(score) for score in SCORES))


class TestAnOracleReading(BaseTestSuite):
    """Every referee read as its mean over the starts, its score's lowest and highest beside it."""

    def test_each_reading_is_its_mean_over_the_starts(self, reading: OracleReading) -> None:
        readings = reading.readings()

        mean = sum(SCORES) / len(SCORES)
        assert readings[HEADLINE][SCORE_READING] == pytest.approx(mean)
        assert readings[HEADLINE][PART] == pytest.approx(2.0 * mean)
        assert readings[SECOND][SCORE_READING] == pytest.approx(10.0 - mean)

    def test_the_score_keeps_its_lowest_and_highest_beside_the_mean(self, reading: OracleReading) -> None:
        readings = reading.readings()

        assert (readings[HEADLINE][LOWEST_READING], readings[HEADLINE][HIGHEST_READING]) == (min(SCORES), max(SCORES))
        assert (readings[SECOND][LOWEST_READING], readings[SECOND][HIGHEST_READING]) == (
            10.0 - max(SCORES),
            10.0 - min(SCORES),
        )

    def test_the_referees_and_readings_keep_the_judgments_order(self, reading: OracleReading) -> None:
        readings = reading.readings()

        assert list(readings) == [HEADLINE, SECOND]
        assert list(readings[HEADLINE]) == [SCORE_READING, PART, LOWEST_READING, HIGHEST_READING]

    def test_the_typical_start_scores_nearest_the_mean(self, reading: OracleReading) -> None:
        """The mean is 2.625, and 2.0 lies nearest it."""
        assert reading.typical(HEADLINE) == SCORES.index(2.0)
