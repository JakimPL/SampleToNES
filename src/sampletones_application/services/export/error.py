from dataclasses import dataclass

from sampletones_application.services.export.kind import ExportKind


@dataclass(frozen=True, eq=False)
class ExportError:
    """A failed export, carrying the exception the result dialog reports.

    Attributes:
        kind: The artefact the run set out to produce.
        exception: The failure raised while writing.
    """

    kind: ExportKind
    exception: Exception
