from typing import Final

import numpy as np

RAMP_STEP: Final[float] = 2.0**-20


def ramp(frames: int, *, start: int = 0) -> np.ndarray:
    """Test audio whose every sample states its own index in the document it stands for.

    A sample holds ``index * RAMP_STEP``, a power of two apart, so float32 carries each index exactly up to
    a million samples while every value stays below full scale. What a device received can then be read
    back as the document positions it played, which shows a gap, a repeat, a seek and the rate at once.
    """
    return (np.arange(start, start + frames, dtype=np.float64) * RAMP_STEP).astype(np.float32)


def ramp_indices(samples: np.ndarray) -> np.ndarray:
    """The document indices a run of ramp samples states, read back to the nearest whole index."""
    return np.rint(samples.astype(np.float64) / RAMP_STEP).astype(np.int64)
