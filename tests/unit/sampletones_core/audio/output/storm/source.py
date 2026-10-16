import threading
import time
from dataclasses import dataclass
from typing import Final, Optional

import numpy as np

from sampletones_core.audio.output import Fill, Tagged
from sampletones_core.audio.output.source import FailureReport

LEVEL_STEP: Final[float] = 2.0**-12
STORM_FAILURE: Final[str] = "The storm failed the source"


class StormFailure(RuntimeError):
    """A failure the storm gave a source."""


@dataclass(frozen=True)
class StormMark:
    """A position a storm source reports for a block it filled.

    Attributes:
        serial: How many blocks the source filled, this one included.
        position: The frame the source stands at after the block, which a seek moves.
    """

    serial: int
    position: int


@dataclass(frozen=True)
class StormSound:
    """What one storm source plays.

    Attributes:
        identity: The sound's number, which every sample it plays states as its level.
        length: The frames it plays before it finishes, or ``None`` for a sound that plays until it is ended.
        failing_read: The read that fails, counted from the first, or ``None`` for a sound whose reads succeed.
        read_seconds: How long each read takes.
    """

    identity: int
    length: Optional[int]
    failing_read: Optional[int]
    read_seconds: float


def level_of(identity: int) -> float:
    """The level every sample of the sound numbered ``identity`` holds, exact in float32 and below full scale."""
    return (identity + 1) * LEVEL_STEP


def identity_of(level: float) -> int:
    """The number of the sound whose samples hold ``level``."""
    return round(level / LEVEL_STEP) - 1


class StormSource:
    """A sound whose every sample states its number, so each block the device took names the sound it carried.

    The source plays at whatever rate the stream takes, since its level is the same at every rate. Each block
    it fills reports a mark, and a seek moves the position the marks carry. A failure told aside reaches the
    playback from the storm's own thread, as a source failing on a thread of its own tells it.
    """

    def __init__(self, sound: StormSound) -> None:
        self.sound = sound
        self._lock = threading.Lock()
        self._failed: Optional[FailureReport] = None
        self._closed: bool = False
        self._reads: int = 0
        self._serial: int = 0
        self._played: int = 0
        self._position: int = 0

    def begin(self, output_rate: int, failed: FailureReport) -> None:
        with self._lock:
            self._failed = failed

    def read_into(self, block: np.ndarray) -> Fill[StormMark]:
        """Fills ``block`` with the sound's level, short once its length runs out.

        Raises:
            StormFailure: At the read the sound fails at.
        """
        with self._lock:
            closed = self._closed

        if closed:
            return Fill(frames=0, reports=())

        self._reads += 1
        if self.sound.failing_read is not None and self._reads >= self.sound.failing_read:
            raise StormFailure(STORM_FAILURE)

        time.sleep(self.sound.read_seconds)
        frames = self._frames(len(block))
        if frames == 0:
            return Fill(frames=0, reports=())

        block[:frames] = level_of(self.sound.identity)
        self._played += frames
        self._position += frames
        self._serial += 1
        return Fill(frames=frames, reports=(Tagged(offset=frames, report=StormMark(self._serial, self._position)),))

    def seek(self, position: int) -> None:
        self._position = position

    def fail_aside(self) -> bool:
        """Tells the playback of a failure met between reads; answers whether a stream had begun the source."""
        with self._lock:
            failed = self._failed

        if failed is None:
            return False

        failed(StormFailure(STORM_FAILURE))
        return True

    def close(self) -> None:
        with self._lock:
            self._closed = True

    def _frames(self, block_frames: int) -> int:
        if self.sound.length is None:
            return block_frames

        return min(block_frames, self.sound.length - self._played)
