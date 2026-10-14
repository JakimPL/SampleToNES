from typing import Final

import numpy as np

from sampletones_core.audio.output import mixed_block

FRAMES: Final[int] = 8
UNITY: Final[float] = 1.0
HALF: Final[float] = 0.5
BOOST: Final[float] = 4.0


class TestMixedBlock:
    """A block is every playback at its gain, summed, padded with silence and held within full scale."""

    def test_one_playback_at_unity_passes_unchanged(self) -> None:
        samples = np.linspace(-0.5, 0.5, FRAMES, dtype=np.float32)

        np.testing.assert_array_equal(mixed_block([(samples, UNITY)], FRAMES), samples)

    def test_a_gain_scales_its_playback(self) -> None:
        samples = np.full(FRAMES, 0.5, dtype=np.float32)

        np.testing.assert_allclose(mixed_block([(samples, HALF)], FRAMES), np.full(FRAMES, 0.25))

    def test_a_short_fill_leaves_the_rest_silent(self) -> None:
        block = mixed_block([(np.full(3, 0.5, dtype=np.float32), UNITY)], FRAMES)

        np.testing.assert_array_equal(block[3:], np.zeros(FRAMES - 3, dtype=np.float32))
        assert len(block) == FRAMES

    def test_a_boost_past_full_scale_is_clipped(self) -> None:
        block = mixed_block([(np.full(FRAMES, 0.5, dtype=np.float32), BOOST)], FRAMES)

        np.testing.assert_array_equal(block, np.ones(FRAMES, dtype=np.float32))

    def test_no_playback_writes_silence(self) -> None:
        np.testing.assert_array_equal(mixed_block([], FRAMES), np.zeros(FRAMES, dtype=np.float32))
