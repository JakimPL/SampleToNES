from typing import Final, Optional

import numpy as np

from sampletones_core.audio.output import Fill
from sampletones_core.audio.output.source import FailureReport

SOURCE_FAILURE: Final[str] = "The source failed"


class AsideFailingSource:
    """A source filling every block, whose failure the case tells on a thread of its own, between reads."""

    def __init__(self) -> None:
        self._failed: Optional[FailureReport] = None
        self.error = RuntimeError(SOURCE_FAILURE)

    def begin(self, output_rate: int, failed: FailureReport) -> None:
        self._failed = failed

    def read_into(self, block: np.ndarray) -> Fill[int]:
        return Fill(frames=len(block), reports=())

    def fail(self) -> None:
        assert self._failed is not None, "the source failed before the stream began it"
        self._failed(self.error)

    def close(self) -> None:
        return None


class FailingSource:
    """A source whose read fails at the block the case names, after filling every block before it."""

    def __init__(self, *, failing_read: int) -> None:
        self._failing_read = failing_read
        self.reads: int = 0
        self.error = RuntimeError(SOURCE_FAILURE)

    def begin(self, output_rate: int, _failed: FailureReport) -> None:
        return None

    def read_into(self, block: np.ndarray) -> Fill[int]:
        self.reads += 1
        if self.reads > self._failing_read:
            raise self.error

        return Fill(frames=len(block), reports=())

    def close(self) -> None:
        return None
