from typing import Optional

import numpy as np

from sampletones_core.exporters import Features


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
