from dataclasses import dataclass
from typing import Optional

from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_tools.tracker_playback.comparison import TraceComparison
from sampletones_tools.tracker_playback.corpus.build import CorpusProject


@dataclass(frozen=True)
class ProjectOutcome:
    """How one project of the corpus fared: what the tracker played of it, and what its export left out.

    Attributes:
        project: The project compared.
        comparison: How the tracker played it against the application.
        skipped_rows: How many rows the export wrote as note cuts for lack of an instrument.
        truncation: The instruments a macro shortened, or ``None`` where every one fit.
    """

    project: CorpusProject
    comparison: TraceComparison
    skipped_rows: int
    truncation: Optional[EnvelopeTruncation]
