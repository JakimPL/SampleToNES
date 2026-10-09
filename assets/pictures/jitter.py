from typing import Final

import numpy as np
from PIL import Image

JITTER_FRACTION: Final[float] = 1e-3
BLOCK: Final[int] = 3
JITTER_BLOCK_PIXELS: Final[int] = 3


def is_jitter(kept: Image.Image, drawn: Image.Image) -> bool:
    """Whether ``drawn`` differs from ``kept`` only by the renderer's jitter, so the kept picture stands.

    A software renderer lands an anti-aliased edge a fraction of a pixel differently from one process
    to the next, which flips a scatter of single pixels along text and plot edges. A change to the
    interface alters a region instead: a glyph, a control or a line moves as a block. The two are told
    apart by density: jitter leaves every 3 by 3 block of the frame with a few changed pixels at most,
    and keeps the changed pixels a small fraction of the whole.
    """
    if kept.size != drawn.size:
        return False

    changed = np.any(
        np.asarray(kept.convert("RGB")) != np.asarray(drawn.convert("RGB")),
        axis=2,
    )
    if not changed.any():
        return True

    if changed.mean() > JITTER_FRACTION:
        return False

    return int(block_counts(changed).max()) <= JITTER_BLOCK_PIXELS


def block_counts(changed: np.ndarray) -> np.ndarray:
    """How many changed pixels each 3 by 3 block centered on a pixel holds, at every pixel of the frame."""
    padded = np.pad(changed.astype(np.int32), BLOCK // 2)
    height, width = changed.shape
    counts = np.zeros((height, width), dtype=np.int32)
    for row_offset in range(BLOCK):
        for column_offset in range(BLOCK):
            counts += padded[
                row_offset : row_offset + height,
                column_offset : column_offset + width,
            ]

    return counts
