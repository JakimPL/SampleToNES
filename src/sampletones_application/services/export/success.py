from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from sampletones_application.services.export.kind import ExportKind
from sampletones_core.exporters.skipped import SkippedRow
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.format import ExportFormat


@dataclass(frozen=True)
class ExportSuccess:
    """A completed export, with the path it wrote and what the file kept.

    Attributes:
        kind: The artifact the run produced.
        filepath: A file the run wrote, which a batch reports as the first of its slices.
        export_format: The format the run wrote, and ``None`` for an audio export.
        truncation: What the target format's item limit left out, and ``None`` when
            the export carries every frame.
        skipped_rows: The rows of the song written as a note cut, because the voice they name
            has no instrument on their channel.
    """

    kind: ExportKind
    filepath: Path
    export_format: Optional[ExportFormat]
    truncation: Optional[EnvelopeTruncation]
    skipped_rows: Tuple[SkippedRow, ...]
