from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sampletones_core.famitracker.specification.sequences import MAX_SEQUENCE_ITEMS


@dataclass(frozen=True)
class SequenceTruncation:
    """The frames of an envelope the FamiTracker sequence limit leaves out.

    Attributes:
        frames: The frame count the exported sequences carry.
        source_frames: The frame count the envelopes arrived with.
    """

    frames: int
    source_frames: int

    @classmethod
    def measure(cls, source_frames: int) -> Optional[SequenceTruncation]:
        """Reports what an export of this many frames keeps.

        Args:
            source_frames: The frame count the envelopes arrived with.

        Returns:
            Optional[SequenceTruncation]: The shortening the limit imposes, and ``None``
                when the envelopes fit whole.
        """
        if source_frames <= MAX_SEQUENCE_ITEMS:
            return None

        return cls(frames=MAX_SEQUENCE_ITEMS, source_frames=source_frames)
