from dataclasses import dataclass
from enum import Enum
from typing import Optional, Self


class EndCause(Enum):
    """Why a playback ended, as its one end report names it."""

    FINISHED = "finished"
    STOPPED = "stopped"
    TAKEN = "taken"
    FAILED = "failed"


@dataclass(frozen=True)
class Ending:
    """How a playback ended: its cause, and the failure behind it where it failed.

    Attributes:
        cause: Why the playback ended.
        error: The failure, present exactly when the cause is ``FAILED``.

    Raises:
        ValueError: If a failure comes without its error, or an error with another cause.
    """

    cause: EndCause
    error: Optional[Exception]

    def __post_init__(self) -> None:
        if (self.cause is EndCause.FAILED) != (self.error is not None):
            raise ValueError(f"An ending caused by {self.cause.value} cannot carry the error {self.error!r}")

    @classmethod
    def of(cls, cause: EndCause) -> Self:
        """An ending by a finish, a stop or a takeover."""
        return cls(cause=cause, error=None)

    @classmethod
    def failure(cls, error: Exception) -> Self:
        return cls(cause=EndCause.FAILED, error=error)
