import pytest

from sampletones_core.famitracker.sequences.truncation import SequenceTruncation
from sampletones_core.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS


class TestSequenceTruncationMeasure:
    @pytest.mark.parametrize(
        "source_frames",
        [0, 1, MAX_SEQUENCE_ITEMS],
        ids=["empty", "single", "at_the_limit"],
    )
    def test_an_envelope_within_the_limit_reports_nothing(self, source_frames: int) -> None:
        assert SequenceTruncation.measure(source_frames) is None

    def test_an_envelope_beyond_the_limit_reports_both_counts(self) -> None:
        truncation = SequenceTruncation.measure(300)
        assert truncation == SequenceTruncation(frames=MAX_SEQUENCE_ITEMS, source_frames=300)
