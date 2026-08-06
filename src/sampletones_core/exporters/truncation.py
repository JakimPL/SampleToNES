from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class EnvelopeTruncation:
    """The frames a target format's item limit leaves out of the instruments one export wrote.

    Attributes:
        frames: The frame count a shortened instrument carries.
        source_frames: The longest envelope the export was given.
        instruments: How many written instruments were shortened.
    """

    frames: int
    source_frames: int
    instruments: int

    @classmethod
    def measure(cls, source_frames: int, limit: Optional[int]) -> Optional[EnvelopeTruncation]:
        """Reports what an export of one instrument's envelopes keeps.

        Args:
            source_frames: The frame count the envelopes arrived with.
            limit: The most items the target format stores, or ``None`` when it is unbounded.

        Returns:
            Optional[EnvelopeTruncation]: The shortening the limit imposes, and ``None``
                when the envelopes fit whole.
        """
        if limit is None or source_frames <= limit:
            return None

        return cls(frames=limit, source_frames=source_frames, instruments=1)

    @classmethod
    def summarize(
        cls,
        truncations: Sequence[Optional[EnvelopeTruncation]],
    ) -> Optional[EnvelopeTruncation]:
        """Gathers the per-instrument shortenings of one export into a single report.

        Args:
            truncations: One entry per written instrument, ``None`` where it fit whole.

        Returns:
            Optional[EnvelopeTruncation]: The summary, and ``None`` when every instrument
                carries its whole envelope.
        """
        shortened = [truncation for truncation in truncations if truncation is not None]
        if not shortened:
            return None

        return cls(
            frames=min(truncation.frames for truncation in shortened),
            source_frames=max(truncation.source_frames for truncation in shortened),
            instruments=sum(truncation.instruments for truncation in shortened),
        )
