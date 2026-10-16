from typing import Protocol

import numpy as np

from sampletones_core.audio.output.ending import Ending
from sampletones_shared.types.callback import VoidCallback


class PlaybackFeed(Protocol):
    """A playback as the output drives it, whatever its source reports.

    The output takes a playback's commands under its lock at the step that mixes it, and the writer reads it,
    hands on the positions of a block the device took, and tells it its end. A close comes from whichever
    thread decided the end, to wake a read waiting for the sound. The output keys its decisions by the
    playback itself, so a playback hashes by its identity.
    """

    def __hash__(self) -> int: ...

    def enqueue(self, action: VoidCallback) -> None:
        """Keeps a command the output accepted for the playback's next read."""

    def take_commands(self) -> None:
        """Takes the commands kept so far, to run before the read that follows."""

    def read_into(self, block: np.ndarray, *, output_rate: int) -> int:
        """Runs the commands taken, reads the next block from the source, and answers how many frames it wrote.

        Raises:
            Exception: Whatever the source or a command fails with, which ends the playback as a failure.
        """

    def heard(self) -> None:
        """Hands on the positions of the block read last, which the device has taken."""

    def end(self, ending: Ending) -> None:
        """Hands on the playback's one end report."""

    def close(self) -> None:
        """Lets the source go, waking a read waiting for its sound."""


class PlaybackControl(Protocol):
    """What a playback asks of the output it plays on, on its owner's behalf."""

    def is_engaged(self, feed: PlaybackFeed) -> bool:
        """Whether the playback holds the output, from its claim until its end is decided."""

    def is_paused(self, feed: PlaybackFeed) -> bool: ...

    def pause(self, feed: PlaybackFeed) -> bool: ...

    def resume(self, feed: PlaybackFeed) -> bool: ...

    def stop(self, feed: PlaybackFeed) -> bool: ...

    def command(self, feed: PlaybackFeed, action: VoidCallback) -> bool:
        """Runs ``action`` on the writer's thread before the playback's next read; answers whether it still plays."""

    def fail(self, feed: PlaybackFeed, error: Exception) -> bool:
        """Ends the playback with a failure its source met between reads; answers whether the failure decided it."""
