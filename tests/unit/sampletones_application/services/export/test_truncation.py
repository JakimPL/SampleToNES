from sampletones_application.services.export.truncation import ExportTruncation
from sampletones_core.famitracker.sequences.truncation import SequenceTruncation


class TestExportTruncationSummarize:
    def test_a_complete_export_summarizes_to_nothing(self) -> None:
        assert ExportTruncation.summarize([None, None]) is None

    def test_an_empty_export_summarizes_to_nothing(self) -> None:
        assert ExportTruncation.summarize([]) is None

    def test_the_summary_spans_every_shortened_instrument(self) -> None:
        summary = ExportTruncation.summarize(
            [
                None,
                SequenceTruncation(frames=252, source_frames=300),
                SequenceTruncation(frames=252, source_frames=480),
            ]
        )
        assert summary == ExportTruncation(frames=252, source_frames=480, instruments=2)
