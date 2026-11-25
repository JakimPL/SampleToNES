import math
from dataclasses import dataclass
from typing import Dict, Final, List, Optional

import pytest

from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.renders import RenderRecord
from sampletones_tools.calibration.rows import LOG_GAP, CalibrationRow, log_gap, recorded_rows
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

AUDIO: Final[str] = "auditory"
TRUTH: Final[str] = "transcription"


def _record(judgments: Dict[str, Dict[str, float]], silence: Dict[str, float]) -> RenderRecord:
    return RenderRecord(
        variant="cqt-pe1",
        item="a",
        position=0,
        family="notes",
        category="notes-pulse",
        timelines={},
        judgments=judgments,
        silence=silence,
    )


class TestLogGap(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        score: float
        silence: float
        gap: Optional[float]

    test_cases = (
        TestCase(score=2.0, silence=8.0, gap=math.log(0.25), label="closer_than_silence"),
        TestCase(score=8.0, silence=8.0, gap=0.0, label="as_close_as_silence"),
        TestCase(score=16.0, silence=8.0, gap=math.log(2.0), label="farther_than_silence"),
        TestCase(score=0.0, silence=8.0, gap=None, label="exact_render"),
        TestCase(score=2.0, silence=0.0, gap=None, label="silent_recording"),
        TestCase(score=-1.0, silence=8.0, gap=None, label="negative_score"),
        TestCase(score=2.0, silence=-8.0, gap=None, label="negative_silence"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_gap_is_the_logarithm_of_score_over_silence_where_both_are_positive(self, test_case: TestCase) -> None:
        assert log_gap(test_case.score, test_case.silence) == test_case.gap


class TestRecordedRows:
    def test_an_audio_score_also_reads_as_its_log_gap_to_silence(self) -> None:
        rows = recorded_rows(_record({AUDIO: {SCORE_READING: 2.0}}, {AUDIO: 8.0}))

        gaps = [row.score for row in rows if row.component == LOG_GAP]
        assert gaps == [pytest.approx(math.log(2.0 / 8.0))]

    @pytest.mark.parametrize("score, silence", [(0.0, 8.0), (2.0, 0.0)], ids=["exact_render", "silent_recording"])
    def test_a_score_or_silence_of_zero_reads_no_log_gap(self, score: float, silence: float) -> None:
        rows = recorded_rows(_record({AUDIO: {SCORE_READING: score}}, {AUDIO: silence}))

        assert [row.component for row in rows] == [SCORE_READING]

    def test_a_referee_silence_has_no_score_for_reads_no_log_gap(self) -> None:
        rows = recorded_rows(_record({TRUTH: {SCORE_READING: 0.5}}, {}))

        assert [(row.referee, row.component) for row in rows] == [(TRUTH, SCORE_READING)]

    def test_a_silence_score_without_a_judgment_adds_no_row(self) -> None:
        rows = recorded_rows(_record({TRUTH: {SCORE_READING: 0.5}}, {AUDIO: 8.0}))

        assert [row.referee for row in rows] == [TRUTH]

    def test_the_rows_keep_the_record_s_order_each_log_gap_after_its_referee_s_readings(self) -> None:
        judgments = {AUDIO: {SCORE_READING: 2.0, "level": 1.0}, TRUTH: {SCORE_READING: 0.5, "missed": 0.25}}

        rows = recorded_rows(_record(judgments, {AUDIO: 8.0}))

        assert [(row.referee, row.component) for row in rows] == [
            (AUDIO, SCORE_READING),
            (AUDIO, "level"),
            (AUDIO, LOG_GAP),
            (TRUTH, SCORE_READING),
            (TRUTH, "missed"),
        ]

    def test_every_row_carries_the_record_s_sound(self) -> None:
        record = _record({AUDIO: {SCORE_READING: 2.0}}, {})

        (row,) = recorded_rows(record)

        assert row == CalibrationRow(
            variant=record.variant,
            item=record.item,
            family=record.family,
            category=record.category,
            referee=AUDIO,
            component=SCORE_READING,
            score=2.0,
        )

    def test_a_record_of_no_judgment_holds_no_row(self) -> None:
        rows: List[CalibrationRow] = recorded_rows(_record({}, {}))

        assert not rows

    def test_reading_rows_leaves_the_record_unchanged(self) -> None:
        record = _record({AUDIO: {SCORE_READING: 2.0}}, {AUDIO: 8.0})

        recorded_rows(record)

        assert record.judgments == {AUDIO: {SCORE_READING: 2.0}}
