from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sampletones_application.services.export.kind import ExportKind
from sampletones_core.exporters.truncation import EnvelopeTruncation


@dataclass(frozen=True)
class ExportSuccess:
    """A completed export, with the path it wrote and what the file kept.

    Attributes:
        kind: The artefact the run produced.
        filepath: The file written, or the directory a batch of instruments filled.
        truncation: What the target format's item limit left out, and ``None`` when
            the export carries every frame.
    """

    kind: ExportKind
    filepath: Path
    truncation: Optional[EnvelopeTruncation]
