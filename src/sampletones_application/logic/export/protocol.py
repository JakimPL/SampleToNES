from typing import Callable, Protocol

from sampletones_application.services.export.result import ExportResult


class ExportProgressServiceProtocol(Protocol):
    """The slice of the export service the progress dialog's logic drives.

    Typing the collaborator structurally keeps the logic layer independent of the service
    implementation; the composition root supplies the real service.
    """

    def subscribe(self, handler: Callable[[ExportResult], None]) -> None: ...

    def cancel(self) -> None: ...

    def is_running(self) -> bool: ...

    def shutdown(self) -> None: ...
