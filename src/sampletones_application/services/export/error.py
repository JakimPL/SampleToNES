from dataclasses import dataclass
from typing import Optional

from sampletones_application.services.export.kind import ExportKind
from sampletones_core.trackers.format import TrackerFormat


@dataclass(frozen=True, eq=False)
class ExportError:
    """A failed export, carrying the exception the result dialog reports.

    Attributes:
        kind: The artefact the run set out to produce.
        tracker_format: The format the run set out to write, and ``None`` for an audio export.
        exception: The failure raised while writing.
    """

    kind: ExportKind
    tracker_format: Optional[TrackerFormat]
    exception: Exception
