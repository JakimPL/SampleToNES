from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sampletones_application.services.export.kind import ExportKind
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.trackers.format import TrackerFormat


@dataclass(frozen=True)
class ExportSuccess:
    """A completed export, with the path it wrote and what the file kept.

    Attributes:
        kind: The artefact the run produced.
        filepath: A file the run wrote, which a batch reports as the first of its slices.
        tracker_format: The format the run wrote, and ``None`` for an audio export.
        truncation: What the target format's item limit left out, and ``None`` when
            the export carries every frame.
    """

    kind: ExportKind
    filepath: Path
    tracker_format: Optional[TrackerFormat]
    truncation: Optional[EnvelopeTruncation]
