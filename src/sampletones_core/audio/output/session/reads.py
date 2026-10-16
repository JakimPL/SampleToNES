from dataclasses import dataclass
from enum import Enum
from typing import Optional, Self


class ReadKind(Enum):
    """How a playback's source answered the read for one block."""

    FILLED = "filled"
    LAST = "last"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceRead:
    """How a playback's source answered the read for one block: filled it, ended in it, or failed.

    Attributes:
        kind: How the read went.
        error: What the source failed with, present exactly when the read failed.

    Raises:
        ValueError: If a failed read comes without its error, or another read with one.
    """

    kind: ReadKind
    error: Optional[Exception]

    def __post_init__(self) -> None:
        if (self.kind is ReadKind.FAILED) != (self.error is not None):
            raise ValueError(f"A {self.kind.value} read cannot carry the error {self.error!r}")

    @classmethod
    def filled(cls) -> Self:
        return cls(kind=ReadKind.FILLED, error=None)

    @classmethod
    def last(cls) -> Self:
        """A read holding the source's last frame."""
        return cls(kind=ReadKind.LAST, error=None)

    @classmethod
    def failed(cls, error: Exception) -> Self:
        return cls(kind=ReadKind.FAILED, error=error)
