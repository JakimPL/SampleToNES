from dataclasses import dataclass
from typing import Optional, Tuple

from sampletones_core.exporters.skipped import SkippedRow
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_tools.tracker_playback.comparison import TraceComparison
from sampletones_tools.tracker_playback.projects import CheckedProject


@dataclass(frozen=True)
class ProjectOutcome:
    """How one checked project fared: what the tracker played of it, and what its export left out.

    Attributes:
        project: The project compared.
        comparison: How the tracker played it against the application.
        skipped_rows: The rows the export wrote other than the song plays them, each with why.
        truncation: The instruments a macro shortened, or ``None`` where every one fit.
    """

    project: CheckedProject
    comparison: TraceComparison
    skipped_rows: Tuple[SkippedRow, ...]
    truncation: Optional[EnvelopeTruncation]
