from typing import Final

import numpy as np
import soxr

from sampletones_core.audio.processing import silence

QUALITY: Final[str] = "HQ"
MONO: Final[int] = 1


class BlockResampler:
    """A run of samples at one rate turned into output at another, as much as each block asks for.

    The output stands in an exact relation to the input: output sample ``k`` lies at input position
    ``k * input_rate / output_rate``. The resampler holds some output back while it works, so it is fed
    input until a block's worth of output stands ready, and flushed once the input runs out.

    It wraps soxr's streaming resampler. Its quirk: a stream flushed once takes no further input until it is
    cleared, so a new run, after a seek or a replacement, starts with ``restart``.
    """

    def __init__(self, *, input_rate: int, output_rate: int) -> None:
        self._stream = soxr.ResampleStream(input_rate, output_rate, MONO, dtype="float32", quality=QUALITY)
        self._ready: np.ndarray = silence(0)
        self._flushed: bool = False

    @property
    def flushed(self) -> bool:
        """Whether the run's last output stands ready, the input having run out."""
        return self._flushed

    def restart(self) -> None:
        """Forgets the run so far, for a run starting somewhere else."""
        self._stream.clear()
        self._ready = silence(0)
        self._flushed = False

    def wants(self, frames: int) -> bool:
        """Whether fewer than ``frames`` output samples stand ready while the run still takes input."""
        return not self._flushed and len(self._ready) < frames

    def feed(self, chunk: np.ndarray, *, last: bool) -> None:
        """Takes the run's next input, flushing the rest of the output where ``last`` says the input ends."""
        output = np.asarray(self._stream.resample_chunk(chunk, last=last), dtype=np.float32)
        self._ready = np.concatenate([self._ready, output])
        self._flushed = last

    def take(self, frames: int) -> np.ndarray:
        """Hands out up to ``frames`` of the output standing ready, oldest first."""
        taken, self._ready = self._ready[:frames], self._ready[frames:]
        return taken
