from typing import Final

import pytest

from sampletones_core.exports.progress import (
    SILENT_REPORTER,
    ExportProgress,
    announce,
)
from sampletones_core.exports.stage import ExportStage
from sampletones_shared.exceptions import OperationCancelled
from tests.suite.progress import FIRST_REPORT, RecordingReporter

WRITTEN: Final[int] = 3
TO_WRITE: Final[int] = 8
UNMEASURED: None = None


class TestWhatACallerHearsFromAnExport:
    """A run says which stage it is in and how far that stage has come."""

    def test_a_stage_reaches_the_caller_with_what_it_has_covered(self) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        announce(reporter, ExportStage.WRITING, WRITTEN, TO_WRITE)
        assert reporter.last == ExportProgress(stage=ExportStage.WRITING, completed=WRITTEN, total=TO_WRITE)

    def test_a_stage_only_the_data_ends_states_no_length(self) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter()
        announce(reporter, ExportStage.COMPRESSING, WRITTEN, UNMEASURED)
        assert reporter.last.total is None

    def test_a_caller_watching_nothing_lets_every_stage_through(self) -> None:
        announce(SILENT_REPORTER, ExportStage.WALKING, WRITTEN, TO_WRITE)


class TestWithdrawingARun:
    """A caller that stops wanting the answer stops the run producing it."""

    def test_a_withdrawn_run_unwinds_where_it_was_told(self) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        with pytest.raises(OperationCancelled):
            announce(reporter, ExportStage.WRITING, WRITTEN, TO_WRITE)

    def test_a_withdrawal_names_the_stage_it_landed_on(self) -> None:
        reporter: RecordingReporter[ExportProgress] = RecordingReporter(withdraw_at=FIRST_REPORT)
        with pytest.raises(OperationCancelled, match=ExportStage.WRITING.value):
            announce(reporter, ExportStage.WRITING, WRITTEN, TO_WRITE)
