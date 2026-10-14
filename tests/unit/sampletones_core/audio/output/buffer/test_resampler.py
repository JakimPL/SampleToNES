from typing import Final

import numpy as np

from sampletones_core.audio.output import BlockResampler
from tests.suite.audio.ramp import ramp

INPUT_RATE: Final[int] = 44100
OUTPUT_RATE: Final[int] = 48000
LENGTH: Final[int] = 5000
CHUNK: Final[int] = 700


def _run(resampler: BlockResampler, audio: np.ndarray) -> np.ndarray:
    """Feeds ``audio`` in chunks until it runs out, and hands out all the output."""
    for start in range(0, len(audio), CHUNK):
        resampler.feed(audio[start : start + CHUNK], last=start + CHUNK >= len(audio))

    return resampler.take(len(audio) * 2)


class TestRuns:
    """A run comes out at the output rate's length, and a restarted run comes out as a fresh one does."""

    def test_a_flushed_run_comes_out_at_its_length_in_the_output_rate(self) -> None:
        resampler = BlockResampler(input_rate=INPUT_RATE, output_rate=OUTPUT_RATE)

        output = _run(resampler, ramp(LENGTH))

        assert resampler.flushed
        assert len(output) == round(LENGTH * OUTPUT_RATE / INPUT_RATE)

    def test_a_restarted_run_matches_a_fresh_one(self) -> None:
        resampler = BlockResampler(input_rate=INPUT_RATE, output_rate=OUTPUT_RATE)
        _run(resampler, ramp(LENGTH))

        resampler.restart()
        restarted = _run(resampler, ramp(LENGTH, start=LENGTH))

        fresh = _run(BlockResampler(input_rate=INPUT_RATE, output_rate=OUTPUT_RATE), ramp(LENGTH, start=LENGTH))
        np.testing.assert_array_equal(restarted, fresh)

    def test_a_resampler_wants_input_until_a_block_stands_ready(self) -> None:
        resampler = BlockResampler(input_rate=INPUT_RATE, output_rate=OUTPUT_RATE)

        assert resampler.wants(CHUNK)
        resampler.feed(ramp(4 * CHUNK), last=False)
        assert not resampler.wants(CHUNK)
        assert len(resampler.take(CHUNK)) == CHUNK
