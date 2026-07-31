from typing import Final

import pytest

from sampletones_core.exporters.truncation import EnvelopeTruncation

ITEM_LIMIT: Final[int] = 252


class TestEnvelopeTruncationMeasure:
    @pytest.mark.parametrize(
        "source_frames",
        [0, 1, ITEM_LIMIT],
        ids=["empty", "single", "at_the_limit"],
    )
    def test_an_envelope_within_the_limit_reports_nothing(self, source_frames: int) -> None:
        assert EnvelopeTruncation.measure(source_frames, ITEM_LIMIT) is None

    def test_an_envelope_beyond_the_limit_reports_both_counts(self) -> None:
        truncation = EnvelopeTruncation.measure(300, ITEM_LIMIT)
        assert truncation == EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=300, instruments=1)

    def test_an_unbounded_format_reports_nothing(self) -> None:
        assert EnvelopeTruncation.measure(100_000, None) is None


class TestEnvelopeTruncationSummarize:
    def test_instruments_that_all_fit_report_nothing(self) -> None:
        assert EnvelopeTruncation.summarize([None, None]) is None

    def test_an_empty_export_reports_nothing(self) -> None:
        assert EnvelopeTruncation.summarize([]) is None

    def test_the_summary_spans_every_shortened_instrument(self) -> None:
        summary = EnvelopeTruncation.summarize(
            [
                None,
                EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=300, instruments=1),
                EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=480, instruments=1),
            ]
        )
        assert summary == EnvelopeTruncation(frames=ITEM_LIMIT, source_frames=480, instruments=2)
