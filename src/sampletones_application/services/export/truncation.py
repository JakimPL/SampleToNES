from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from sampletones_core.famitracker.sequences.truncation import SequenceTruncation


@dataclass(frozen=True)
class ExportTruncation:
    """What the FamiTracker sequence limit left out of the instruments one export wrote.

    Attributes:
        frames: The frame count a shortened instrument carries.
        source_frames: The longest envelope the export was given.
        instruments: How many written instruments were shortened.
    """

    frames: int
    source_frames: int
    instruments: int

    @classmethod
    def summarize(cls, truncations: Sequence[Optional[SequenceTruncation]]) -> Optional[ExportTruncation]:
        """Gathers the per-instrument shortenings of one export into a single report.

        Args:
            truncations: One entry per written instrument, ``None`` where it fit whole.

        Returns:
            Optional[ExportTruncation]: The summary, and ``None`` when every instrument
                carries its whole envelope.
        """
        shortened = [truncation for truncation in truncations if truncation is not None]
        if not shortened:
            return None

        return cls(
            frames=min(truncation.frames for truncation in shortened),
            source_frames=max(truncation.source_frames for truncation in shortened),
            instruments=len(shortened),
        )
