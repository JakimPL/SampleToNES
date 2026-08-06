from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from sampletones_core.exporters.truncation import EnvelopeTruncation


@dataclass(frozen=True)
class ExportArtifact:
    """What one export run left on disk.

    Attributes:
        paths: Every file the run wrote, in write order.
        truncation: What the target format's item limit left out, and ``None`` when
            every instrument carries its whole envelope.
    """

    paths: Tuple[Path, ...]
    truncation: Optional[EnvelopeTruncation]
