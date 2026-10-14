from typing import Protocol


class Pacing(Protocol):
    """How fast the fake device takes what is written to it, which is what holds a writer back."""

    def admit(self, stream: int, frames: int, sample_rate: int) -> None:
        """Returns once the device has room for ``frames`` more frames on ``stream``."""

    def drain(self, stream: int) -> None:
        """Returns once the device has played everything written to ``stream``."""

    def discard(self, stream: int) -> int:
        """Forgets what ``stream`` still holds, wakes a writer waiting on it, and answers the frames dropped."""
