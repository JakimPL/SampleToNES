from pathlib import Path
from typing import Optional

from sampletones_application.categories.dialog import dialog_title, filter_name
from sampletones_application.categories.exports import EXPORT_PROJECT_ELEMENTS
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.export.nsf.logic import NSFExportLogic
from sampletones_application.ui.panels.dialogs.nsf import GUINSFExportWindow
from sampletones_application.utils.file_dialogs.api import save_file_dialog
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.view_model.shared.nsf.view import NSFExportViewModel
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.request import SampleExport
from sampletones_shared.types.callback import VoidCallback


class NSFExportCoordinator:
    """Owns setting a program export up from the reader's side: the dialog, the file it asks for,
    and the hand-over to the run.

    This is the :class:`ExportSetup` of every format a console program is written in, so File >
    Export and the Reconstructions tab open it where the save dialog would otherwise ask for the
    file, naming the format the export is written as. The logic holds the setup, so what is
    orchestrated here is the screen: the window opens over the choices the logic offers and
    follows every view it emits, and the destination is asked for through the OS dialog, titled
    and filtered by the format the setup was opened for.

    The setup claims the application from the dialog opening. Every way out passes through the
    logic's close and tells the application to read the claim again, and Export closes the dialog
    a frame ahead of the run, so the export's own window opens onto a clear screen.
    """

    def __init__(
        self,
        nsf_logic: NSFExportLogic,
        *,
        window: GUINSFExportWindow,
        language_manager: LanguageManager,
        on_activity_changed: VoidCallback,
    ) -> None:
        self._logic = nsf_logic
        self._window = window
        self._on_activity_changed = on_activity_changed
        self._view_model: Optional[NSFExportViewModel] = None
        self._window_open = False

        self._language_manager = language_manager

        self._logic.on_view_changed = self._on_view_changed
        self._logic.on_choose_destination = self._choose_destination

        self._window.on_choices_changed = self._logic.apply
        self._window.on_browse = self._logic.request_destination
        self._window.on_export = self._export
        self._window.on_close = self._close

    @property
    def is_active(self) -> bool:
        """A program export occupies the application from the dialog opening until the run takes over."""
        return self._logic.is_active

    def open_project(self, export_format: ExportFormat) -> None:
        """Offers the open project's song as a program in ``export_format``."""
        self._open(self._logic.open_project(export_format))

    def open_sample(self, export_format: ExportFormat, request: SampleExport) -> None:
        """Offers a reconstruction's slices as a program in ``export_format``."""
        self._open(self._logic.open_sample(export_format, request))

    def _open(self, opened: bool) -> None:
        if not opened:
            return

        self._window_open = True
        self._window.open(self._require_view_model())
        self._on_activity_changed()

    def _on_view_changed(self, view_model: NSFExportViewModel) -> None:
        """Keeps the open window standing at the choices the export stands at."""
        self._view_model = view_model
        if self._window_open:
            self._window.update_view(view_model)

    def _choose_destination(self, destination: Path) -> None:
        """Asks for the file the export writes, starting from the one the dialog stands at."""
        view_model = self._require_view_model()
        elements = EXPORT_PROJECT_ELEMENTS[view_model.export_format]
        filepath = save_file_dialog(
            title=dialog_title(self._language_manager, elements.dialog_title),
            initial_directory=destination.parent,
            default_filename=destination.name,
            filters=(
                FileFilter.for_extensions(
                    filter_name(self._language_manager, elements.filter_name),
                    [view_model.extension],
                ),
            ),
        )

        self._set_destination(filepath)

    @ignore_none_path
    def _set_destination(self, filepath: Path) -> None:
        self._logic.set_destination(filepath)

    def _export(self) -> None:
        """Takes the dialog off screen and starts the export, which the running service holds from there."""
        self._take_off_screen()
        self._logic.start()
        self._release()

    def _close(self) -> None:
        """Takes the dialog off screen and hands the application back."""
        self._take_off_screen()
        self._release()

    def _take_off_screen(self) -> None:
        self._window_open = False
        self._view_model = None
        self._window.hide()

    def _release(self) -> None:
        self._logic.close()
        self._on_activity_changed()

    def _require_view_model(self) -> NSFExportViewModel:
        """The export the dialog opens on.

        Raises:
            SystemError: when the window is raised before the logic offers a view.
        """
        if self._view_model is None:
            raise SystemError("The program export window is opened over the view the logic emits")

        return self._view_model
