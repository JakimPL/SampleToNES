from dataclasses import dataclass
from typing import Optional

from sampletones_application.services.export.kind import ExportKind
from sampletones_core.exports.format import ExportFormat


@dataclass(frozen=True, eq=False)
class ExportError:
    """A failed export, carrying the exception the result dialog reports.

    Attributes:
        kind: The artefact the run set out to produce.
        export_format: The format the run set out to write, and ``None`` for an audio export.
        exception: The failure raised while writing.
    """

    kind: ExportKind
    export_format: Optional[ExportFormat]
    exception: Exception
