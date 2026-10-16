from dataclasses import dataclass
from typing import Callable, Generic, Protocol, Tuple, TypeVar

import numpy as np

ReportT = TypeVar("ReportT")
FailureReport = Callable[[Exception], None]


@dataclass(frozen=True)
class Tagged(Generic[ReportT]):
    """A report a source makes about a block, and the frame of the block it holds after.

    Attributes:
        offset: How many frames of the block the device holds once the report is true.
        report: What the source reports, such as the position it reached.
    """

    offset: int
    report: ReportT


@dataclass(frozen=True)
class Fill(Generic[ReportT]):
    """What one read put into a block: how many frames, and the reports they carry.

    A source fills a block whole until its sound runs out, so a fill shorter than the block is its last.

    Attributes:
        frames: The frames the read wrote, from the start of the block.
        reports: The reports the frames carry, in the order of their offsets.
    """

    frames: int
    reports: Tuple[Tagged[ReportT], ...]

    def ends(self, block: np.ndarray) -> bool:
        """Whether the fill holds the source's last frame, which a fill shorter than its block does."""
        return self.frames < len(block)


class AudioSource(Protocol[ReportT]):
    """What a playback reads its sound from, one block at a time, on the thread writing to the device.

    The writer begins a source at its first read, with the rate of the stream it plays on, so a source
    always plays at the rate the device takes, and with what a failure found between reads is told to,
    which ends the playback at once, sounding or held paused. A read fills the block whole while the sound lasts and
    short once it runs out, so the frames written always follow on from the last read. The reports a read
    returns hold for the frames it wrote, and they reach the owner once the device has taken the block.
    The owner's commands, such as a seek, run on the writer's thread between reads.

    A close comes from any thread, at any moment and as often as an end is decided, so it wakes a read
    waiting for its sound, and every read after it comes up empty.
    """

    def begin(self, output_rate: int, failed: FailureReport, /) -> None:
        """Readies the source for the stream it plays on, which takes ``output_rate`` samples a second.

        Args:
            output_rate: The samples a second the stream takes.
            failed: Ends the playback with a failure the source meets on a thread of its own.
        """

    def read_into(self, block: np.ndarray) -> Fill[ReportT]:
        """Writes the next frames of the sound into ``block``, from its start.

        Raises:
            Exception: Whatever the sound fails with, which ends the playback as a failure.
        """

    def close(self) -> None:
        """Lets the source go, waking any read waiting for its sound."""
