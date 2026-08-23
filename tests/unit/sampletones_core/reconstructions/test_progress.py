from dataclasses import dataclass
from typing import List, Tuple

import pytest

from sampletones_core.reconstructions.progress import (
    ReconstructionProgress,
    announce,
)
from sampletones_core.reconstructions.stage import STAGE_SHARES, ReconstructionStage
from sampletones_shared.exceptions import OperationCancelled
from sampletones_shared.utils.progress import silent_reporter
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.progress import FIRST_REPORT, RecordingReporter

WHOLE: float = 1.0
FRAMES: int = 8


class TestStageShares(BaseTestSuite):
    """Every stage a reconstruction passes through holds a share, and the shares are the whole run.

    A bar crossing the stages reads each one through its share, so a stage the shares forgot would
    leave the bar standing still while that stage ran, and shares summing to anything other than
    the whole would leave it short of its end or past it.
    """

    def test_every_stage_holds_a_share(self) -> None:
        assert set(STAGE_SHARES) == set(ReconstructionStage)

    def test_the_shares_are_the_whole_run(self) -> None:
        assert sum(STAGE_SHARES.values()) == pytest.approx(WHOLE)

    def test_a_stage_begins_where_the_stages_before_it_end(self) -> None:
        stages = list(ReconstructionStage)
        offsets = [stage.offset for stage in stages]

        assert offsets[0] == pytest.approx(0.0)
        for stage, offset, following in zip(stages, offsets, offsets[1:]):
            assert following == pytest.approx(offset + stage.share)

    def test_the_last_stage_ends_on_the_whole_run(self) -> None:
        last = list(ReconstructionStage)[-1]
        assert last.offset + last.share == pytest.approx(WHOLE)


class TestReconstructionFraction(BaseTestSuite):
    """A stage's own count reads as a fraction of the whole reconstruction.

    The stages count in units of their own — frames here, an arrival there — so what a bar shows
    is each stage's progress taken through the share it holds, which is what lets one reading span
    a run that changes what it is counting three times over.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: float
        stage: ReconstructionStage
        completed: int
        total: int

        @property
        def label(self) -> str:
            return f"{self.stage}_{self.completed}_of_{self.total}"

    test_cases = (
        TestCase(stage=ReconstructionStage.LOADING, completed=0, total=1, expected=0.0),
        TestCase(stage=ReconstructionStage.MATCHING, completed=0, total=FRAMES, expected=0.05),
        TestCase(stage=ReconstructionStage.MATCHING, completed=FRAMES, total=FRAMES, expected=0.85),
        TestCase(stage=ReconstructionStage.RENDERING, completed=FRAMES, total=FRAMES, expected=WHOLE),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_fraction_weighs_the_stage_by_its_share(self, test_case: TestCase) -> None:
        progress = ReconstructionProgress(
            stage=test_case.stage,
            completed=test_case.completed,
            total=test_case.total,
        )

        assert progress.fraction == pytest.approx(test_case.expected)

    def test_a_stage_measured_against_nothing_reads_as_its_own_beginning(self) -> None:
        progress = ReconstructionProgress(stage=ReconstructionStage.DECODING, completed=0, total=0)

        assert progress.fraction == pytest.approx(ReconstructionStage.DECODING.offset)

    def test_a_run_read_in_stage_order_never_turns_back(self) -> None:
        readings: List[float] = []
        for stage in ReconstructionStage:
            for completed in range(FRAMES + 1):
                readings.append(ReconstructionProgress(stage=stage, completed=completed, total=FRAMES).fraction)

        assert readings == sorted(readings)
        assert readings[0] == pytest.approx(0.0)
        assert readings[-1] == pytest.approx(WHOLE)


class TestAnnounce(BaseTestSuite):
    """A run tells its reporter how far it has come, and unwinds where the reporter withdraws it."""

    def test_a_report_carries_the_stage_and_its_counts(self) -> None:
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter()

        announce(reporter, ReconstructionStage.MATCHING, 3, FRAMES)

        assert reporter.last == ReconstructionProgress(
            stage=ReconstructionStage.MATCHING,
            completed=3,
            total=FRAMES,
        )

    def test_a_withdrawn_run_unwinds_where_it_stood(self) -> None:
        reporter: RecordingReporter[ReconstructionProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)

        with pytest.raises(OperationCancelled):
            announce(reporter, ReconstructionStage.MATCHING, 0, FRAMES)

    def test_a_caller_watching_nothing_hears_the_run_through(self) -> None:
        readings: Tuple[int, ...] = (0, FRAMES // 2, FRAMES)

        for completed in readings:
            announce(silent_reporter, ReconstructionStage.RENDERING, completed, FRAMES)
