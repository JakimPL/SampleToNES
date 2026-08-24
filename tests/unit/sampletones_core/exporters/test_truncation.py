from typing import Final

from sampletones_core.exporters.truncation import EnvelopeTruncation

ITEM_LIMIT: Final[int] = 252


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
