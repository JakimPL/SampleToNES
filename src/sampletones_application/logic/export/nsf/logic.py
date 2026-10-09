from pathlib import Path
from typing import Callable, Optional

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.export.nsf.draft import NSFExportDraft
from sampletones_application.logic.export.nsf.protocol import (
    NSFExportServiceProtocol,
    NSFProgramBackend,
)
from sampletones_application.logic.export.nsf.source.project import ProjectSource
from sampletones_application.logic.export.nsf.source.protocol import NSFExportSource
from sampletones_application.logic.export.nsf.source.sample import SampleSource
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.shared.nsf.choices import NSFExportChoices
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.exports.request import SampleExport
from sampletones_shared.constants.project import DEFAULT_EXPORT_NAME
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import PathCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import get_filename


class NSFExportLogic(CallbackMixin):
    """Owns setting an NSF export up: what it writes, the program it writes it as, and the file.

    The dialog opens on the program the export writes as its source states it, so a reader
    changing nothing writes what the save dialog alone would have written. Every choice is the
    player's own, held in the form the file states it, and the source places the choices on its
    own ticks once the export is handed over.

    Setting an export up is an exclusive operation, claimed the moment the dialog opens. Handing
    the export over closes the setup in the same call the service starts running in, so the
    application stays busy from the dialog opening until the run reports its outcome.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        session_manager: SessionManager,
        export_service: NSFExportServiceProtocol,
        backend: NSFProgramBackend,
        *,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._project_controller = project_controller
        self._session_manager = session_manager
        self._service = export_service
        self._backend = backend
        self._is_operation_active = is_operation_active
        self._draft: Optional[NSFExportDraft] = None

        self.on_view_changed: Optional[Callable[[NSFExportViewModel], None]] = None
        self.on_choose_destination: Optional[PathCallback] = None

    @property
    def is_active(self) -> bool:
        """An NSF export occupies the application while its setup is open."""
        return self._draft is not None

    def open_project(self) -> bool:
        """Offers the open project's song as a program, reporting whether the setup took over."""
        return self._open(
            ProjectSource(
                request=self._project_controller.export_request,
                name=self._project_controller.name or DEFAULT_EXPORT_NAME,
            )
        )

    def open_sample(self, request: SampleExport) -> bool:
        """Offers a reconstruction's slices as a program, reporting whether the setup took over."""
        return self._open(SampleSource(request=request))

    def apply(self, choices: NSFExportChoices) -> None:
        """Takes the reconciled choices the dialog reports."""
        if self._draft is None:
            return

        self._draft = self._draft.with_choices(choices)
        self._emit_view()

    def request_destination(self) -> None:
        """Asks for the file the export writes, starting from the one standing."""
        self.call(self.on_choose_destination, self._require_draft().destination)

    def set_destination(self, destination: Path) -> None:
        """Writes the export to ``destination``."""
        self._draft = self._require_draft().with_destination(destination)
        self._emit_view()

    def start(self) -> bool:
        """Hands the export to the service under the standing choices, and closes the setup.

        Returns:
            bool: Whether the export was handed over, which a ticked channel is what allows.
        """
        draft = self._draft
        if draft is None or not draft.choices.writable:
            return False

        draft.source.remember_directory(self._session_manager, draft.destination.parent)
        draft.source.submit(
            self._service,
            draft.destination,
            self._backend.choosing(draft.program()),
        )
        self.close()
        return True

    def close(self) -> None:
        """Leaves the setup, releasing the application."""
        self._draft = None

    def _open(self, source: NSFExportSource) -> bool:
        """Sets an export of ``source`` up, where no other exclusive operation holds the application.

        The destination is proposed afresh each time, carrying the source's name into the folder
        that kind of export opens on.
        """
        if self._is_operation_active():
            logger.warning("An exclusive operation is already in progress; the NSF export was not offered")
            return False

        offer = source.offer()
        self._draft = NSFExportDraft(
            source=source,
            offer=offer,
            choices=NSFExportChoices.initial(source.program(), offer),
            destination=source.proposed_directory(self._session_manager)
            / get_filename(source.name, self._backend.extension(source.scope)),
        )
        self._emit_view()
        return True

    def _require_draft(self) -> NSFExportDraft:
        """The export the open dialog sets up.

        Raises:
            SystemError: when the setup is driven while its dialog is closed.
        """
        if self._draft is None:
            raise SystemError("An NSF export is set up only while its dialog is open")

        return self._draft

    def _emit_view(self) -> None:
        self.call(self.on_view_changed, self._require_draft().view())
