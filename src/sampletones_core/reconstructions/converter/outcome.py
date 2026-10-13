from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from .job import ConversionJob


@dataclass(frozen=True)
class SkippedJob:
    """A job a run went on without, and the error that ended it."""

    job: ConversionJob
    exception: Exception


@dataclass(frozen=True)
class ConversionOutcome:
    """What a finished run wrote, in job order, and the jobs it went on without."""

    written: Tuple[Path, ...]
    skipped: Tuple[SkippedJob, ...]
