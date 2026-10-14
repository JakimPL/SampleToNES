from typing import Final

import numpy as np

from sampletones_core.audio.output import mixed_block

FRAMES: Final[int] = 8


class TestMixedBlock:
    """A block is every playback's samples summed, padded with silence and held within full scale."""

    def test_one_playback_passes_unchanged(self) -> None:
        samples = np.linspace(-0.5, 0.5, FRAMES, dtype=np.float32)

        np.testing.assert_array_equal(mixed_block([samples], FRAMES), samples)

    def test_two_playbacks_sum(self) -> None:
        quarter = np.full(FRAMES, 0.25, dtype=np.float32)

        np.testing.assert_array_equal(mixed_block([quarter, quarter], FRAMES), np.full(FRAMES, 0.5))

    def test_a_short_fill_leaves_the_rest_silent(self) -> None:
        block = mixed_block([np.full(3, 0.5, dtype=np.float32)], FRAMES)

        np.testing.assert_array_equal(block[3:], np.zeros(FRAMES - 3, dtype=np.float32))
        assert len(block) == FRAMES

    def test_a_sum_past_full_scale_is_clipped(self) -> None:
        loud = np.full(FRAMES, 2.0, dtype=np.float32)

        np.testing.assert_array_equal(mixed_block([loud], FRAMES), np.ones(FRAMES, dtype=np.float32))

    def test_no_playback_writes_silence(self) -> None:
        np.testing.assert_array_equal(mixed_block([], FRAMES), np.zeros(FRAMES, dtype=np.float32))
