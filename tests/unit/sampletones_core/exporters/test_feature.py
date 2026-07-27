from pathlib import Path
from typing import Optional

import numpy as np

from sampletones_core.exporters import Features
from sampletones_core.famitracker.sequences.truncation import SequenceTruncation
from sampletones_core.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS


def build_features(frames: int, *, duty_cycle_frames: Optional[int] = None) -> Features:
    duty_cycle = None if duty_cycle_frames is None else np.zeros(duty_cycle_frames, dtype=int)
    return Features(
        initial_pitch=60,
        volume=np.full(frames, 15, dtype=int),
        arpeggio=np.zeros(frames, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=duty_cycle,
    )


class TestFrameCount:
    def test_the_longest_populated_dimension_sets_the_count(self) -> None:
        assert build_features(24, duty_cycle_frames=30).frame_count == 30

    def test_absent_dimensions_leave_the_count_to_the_others(self) -> None:
        assert build_features(24).frame_count == 24

    def test_empty_envelopes_count_no_frames(self) -> None:
        assert build_features(0).frame_count == 0


class TestSaveReportsTruncation:
    def test_an_envelope_within_the_limit_reports_nothing(self, tmp_path: Path) -> None:
        features = build_features(MAX_SEQUENCE_ITEMS)
        assert features.save(tmp_path / "short.fti", "Short") is None

    def test_an_envelope_beyond_the_limit_reports_both_counts(self, tmp_path: Path) -> None:
        features = build_features(300)
        truncation = features.save(tmp_path / "long.fti", "Long")
        assert truncation == SequenceTruncation(frames=MAX_SEQUENCE_ITEMS, source_frames=300)

    def test_a_shortened_export_still_writes_the_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "long.fti"
        build_features(300, duty_cycle_frames=300).save(filepath, "Long")
        assert filepath.exists()
