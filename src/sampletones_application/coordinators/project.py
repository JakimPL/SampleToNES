from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

from sampletones_application.categories.elements.global_ import (
    DialogElements,
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.exports import EXPORT_PROJECT_ELEMENTS
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.skipped import SkippedRowMessages
from sampletones_application.categories.truncation import TruncationMessages
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.coordinators.export.setup import ExportSetup
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.services.export.error import ExportError
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.result import ExportResult
from sampletones_application.services.export.service import ExportService
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_MODULE_EXPORTED,
    TAG_GLOBAL_DIALOG_PROJECT_OPEN,
    TAG_GLOBAL_DIALOG_PROJECT_SAVED,
    TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
)
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_core.exporters.skipped import SkippedRow
from sampletones_core.exporters.truncation import EnvelopeTruncation
from sampletones_core.exports.backend import ExportBackend
from sampletones_core.exports.format import ExportFormat
from sampletones_core.exports.scope import ExportScope
from sampletones_shared.constants.project import (
    DEFAULT_EXPORT_NAME,
    DEFAULT_PROJECT_FILENAME,
)
from sampletones_shared.exceptions import (
    LoadProjectError,
    SampleToNESError,
    SerializationError,
)
from sampletones_shared.logger import logger
from sampletones_shared.paths.extensions import EXT_FILE_PROJECT
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.system.paths import get_directory, get_filename


class ProjectCoordinator:
    """
    The single owner of project document lifecycle from the user's perspective.

    - It governs higher-level document operations — opening, saving, creating,
      closing — each with the appropriate save confirmation when unsaved changes
      exist.
    - It is the one place that knows when to ask the user "do you want to save?"
      and what to do with the answer.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        project_manager: ProjectManager,
        session_manager: SessionManager,
        export_service: ExportService,
        *,
        export_backends: Dict[ExportFormat, ExportBackend],
        format_setups: Mapping[ExportFormat, ExportSetup],
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_tab_switch: Callback,
        on_session_state_changed: VoidCallback,
    ) -> None:
        self._project_controller = project_controller
        self._project_manager = project_manager
        self._session_manager = session_manager
        self._export_service = export_service
        self._export_backends = export_backends
        self._format_setups = format_setups
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._skipped_row_messages = SkippedRowMessages.build(language_manager)
        self._truncation_messages = TruncationMessages.for_project(language_manager)
        self._on_tab_switch = on_tab_switch
        self._project_manager.session.on_state_changed = on_session_state_changed
        self._project_manager.on_path_changed = session_manager.set_current_project

        export_service.subscribe(self._on_export_result)

    @property
    def project_name(self) -> Optional[str]:
        name = self._project_manager.session.name
        return name or None

    @property
    def is_unsaved(self) -> bool:
        return self._project_controller.is_dirty

    def guard_new(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets a new project take the open one's place, asking first what becomes of the open one.

        The signature is a :data:`Gate`, so the question leads the new project's conversation.
        """
        self._guard_open(
            title=GlobalDialogTitleElements.NEW_UNSAVED_PROJECT,
            message=GlobalMessageElements.NEW_UNSAVED_PROJECT,
            open_message=GlobalMessageElements.NEW_OPEN_PROJECT,
            proceed=proceed,
            decline=decline,
        )

    def guard_open(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets another project take the open one's place, asking first what becomes of the open one.

        The signature is a :data:`Gate`, so the question leads the opening's conversation.
        """
        self._guard_open(
            title=GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT,
            message=GlobalMessageElements.OPEN_UNSAVED_PROJECT,
            open_message=GlobalMessageElements.OPEN_OPEN_PROJECT,
            proceed=proceed,
            decline=decline,
        )

    def new_project(self) -> None:
        """Puts a new project in place and brings the Sequencer forward."""
        self._project_controller.new()
        self._on_tab_switch(Tab.SEQUENCER)

    def open_project(self) -> None:
        """Opens the project file the reader picks."""
        self._open_dialog()

    def load_project_safely(self, path: Path) -> None:
        """Loads the project a run starts on, the one the session remembers or the one it was given.

        Startup restore happens automatically, so a failed load is recovered silently:
        the stale session pointer is cleared so a missing, moved, or corrupt file leaves
        the next launch starting from a clean slate. Only known domain and I/O failures
        are absorbed; unexpected errors propagate. A project that loads stands for its file,
        so a later save writes there.
        """
        try:
            self._project_controller.load(path)
        except (SampleToNESError, OSError) as exception:
            logger.warning(f"Could not restore project from {logger.format_path(path)}: {exception}")
            self._session_manager.set_current_project(None)

    def guard_close(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets the open project close, asking first to save unsaved changes.

        With no project open there is nothing to close, so the request is turned away. The
        signature is a :data:`Gate`, so the question leads the closing's conversation.
        """
        if not self._project_controller.is_open:
            decline()
            return

        if not self.is_unsaved:
            proceed()
            return

        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
            title=self._title(GlobalDialogTitleElements.CLOSE_UNSAVED_PROJECT),
            message=self._message(GlobalMessageElements.CLOSE_UNSAVED_PROJECT),
            on_save=self._write_project,
            on_confirm=proceed,
            on_cancel=decline,
            ok_label=self._label(DialogElements.DISCARD),
        )

    def close_project(self) -> None:
        self._project_controller.close()

    def guard_exit(self, proceed: VoidCallback, decline: VoidCallback) -> None:
        """Lets the exit go on, asking first to save a project with unsaved changes.

        Save and Exit both go on, so what the exit asks about next is asked in turn, and Cancel
        keeps the application open and turns the exit away.
        """
        if not self.is_unsaved:
            proceed()
            return

        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
            title=self._title(GlobalDialogTitleElements.EXIT_CONFIRMATION),
            message=self._message(GlobalMessageElements.EXIT_UNSAVED_PROJECT),
            on_save=self._write_project,
            on_confirm=proceed,
            on_cancel=decline,
            ok_label=self._label(DialogElements.EXIT),
        )

    def save(self) -> SaveOutcome:
        """Saves the project to its current file, prompting for one when it has none, and says so.

        Reports what the save came to, the way :meth:`_write_project` does.
        """
        return self._announced(self._write_project())

    def save_as_dialog(self) -> SaveOutcome:
        """Prompts for a destination and saves the project there, saying so once it is written."""
        return self._announced(self._write_to_chosen_file())

    def _write_project(self) -> SaveOutcome:
        """Writes the project to its current file, prompting for one when it has none.

        A save prompt waits on this, going on once the project lands on disk and asking again when
        the reader closes the file dialog. The reader asked to go on, so the save goes on without a
        word of its own, and whatever the prompt guards opens alone.
        """
        filepath = self._project_manager.path
        if filepath is None:
            return self._write_to_chosen_file()

        return self._write(filepath)

    def _write_to_chosen_file(self) -> SaveOutcome:
        path = self._session_manager.get_project_path()
        filename = path.name if path.is_file() else DEFAULT_PROJECT_FILENAME
        directory = get_directory(path)
        filepath = save_file_dialog(
            title=self._title(GlobalDialogTitleElements.SAVE_PROJECT),
            initial_directory=directory,
            default_filename=filename,
            filters=self._project_filters(),
        )

        return self._handle_save_as(filepath)

    def _announced(self, outcome: SaveOutcome) -> SaveOutcome:
        """Tells the reader a save they asked for by itself has landed."""
        if outcome is SaveOutcome.WRITTEN:
            self._dialogs.show_info(
                TAG_GLOBAL_DIALOG_PROJECT_SAVED,
                self._message(GlobalMessageElements.PROJECT_SAVED_SUCCESSFULLY),
                self._title(GlobalDialogTitleElements.PROJECT_SAVED),
            )

        return outcome

    def _project_filters(self) -> Tuple[FileFilter, ...]:
        """The single type a project of this application's own is written as and read from."""
        return (
            FileFilter.for_extensions(
                self._filter_name(FileFilterElements.PROJECT),
                [EXT_FILE_PROJECT],
            ),
        )

    def _get_project_filename(self, extension: str) -> str:
        name = self.project_name or DEFAULT_EXPORT_NAME
        return get_filename(name, extension)

    def export_project_dialog(self, export_format: ExportFormat) -> None:
        """Writes the open project in ``export_format``, asking first for what the format leaves open.

        A format with a setup of its own opens it, and that setup asks for the destination with
        the rest of its choices. Every other format asks for the destination through the save
        dialog.

        Args:
            export_format: The format the project is written in.
        """
        if not self._project_controller.is_open:
            return

        if export_format in self._format_setups:
            self._format_setups[export_format].open_project()
            return

        backend = self._export_backends[export_format]
        elements = EXPORT_PROJECT_ELEMENTS[export_format]
        extension = backend.extension(ExportScope.PROJECT)
        path = self._session_manager.get_project_path()
        filepath = save_file_dialog(
            title=self._title(elements.dialog_title),
            initial_directory=get_directory(path),
            default_filename=self._get_project_filename(extension),
            filters=(
                FileFilter.for_extensions(
                    self._filter_name(elements.filter_name),
                    [extension],
                ),
            ),
        )

        self._handle_export_project(filepath, export_format)

    def _open_dialog(self) -> None:
        filepath = open_file_dialog(
            title=self._title(GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT),
            initial_directory=self._session_manager.get_project_path(),
            filters=self._project_filters(),
        )

        self._handle_open(filepath)

    @ignore_none_path
    def _handle_open(self, filepath: Path) -> None:
        self._session_manager.set_project_path(filepath.parent)
        self._load(filepath)

    @ignore_none_path(default=SaveOutcome.CALLED_OFF)
    def _handle_save_as(self, filepath: Path) -> SaveOutcome:
        self._session_manager.set_project_path(filepath.parent)
        return self._write(filepath)

    @ignore_none_path
    def _handle_export_project(self, filepath: Path, export_format: ExportFormat) -> None:
        self._export_service.export_project(
            filepath,
            self._export_backends[export_format],
            self._project_controller.export_request,
        )

    def _load(self, filepath: Path) -> None:
        try:
            self._project_controller.load(filepath)
        except (LoadProjectError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to load project from {filepath}",
            )
            self._dialogs.show_error(exception)
            return

        self._on_tab_switch(Tab.SEQUENCER)

    def _write(self, filepath: Path) -> SaveOutcome:
        try:
            self._project_controller.save(filepath)
        except (SerializationError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Failed to save project to {filepath}",
            )
            self._dialogs.show_error(
                exception,
                self._message(GlobalMessageElements.PROJECT_SAVE_FAILED),
            )
            return SaveOutcome.FAILED

        return SaveOutcome.WRITTEN

    def _on_export_result(self, result: ExportResult) -> None:
        """Reports a finished project export in the words of the format it was written in."""
        match result:
            case ExportSuccess(
                kind=ExportKind.PROJECT,
                export_format=ExportFormat() as export_format,
                skipped_rows=skipped_rows,
                truncation=truncation,
            ):
                self._dialogs.show_info(
                    TAG_GLOBAL_DIALOG_MODULE_EXPORTED,
                    self._exported_message(export_format, skipped_rows, truncation),
                    self._title(GlobalDialogTitleElements.PROJECT_EXPORTED),
                )
            case ExportError(
                kind=ExportKind.PROJECT,
                export_format=ExportFormat() as export_format,
                exception=exception,
            ):
                self._dialogs.show_error(
                    exception,
                    self._message(EXPORT_PROJECT_ELEMENTS[export_format].export_failed_message),
                )

    def _exported_message(
        self,
        export_format: ExportFormat,
        skipped_rows: Tuple[SkippedRow, ...],
        truncation: Optional[EnvelopeTruncation],
    ) -> str:
        """The report of a written project, followed by what the format left out of it.

        The rows the format wrote as a note cut come first, then the instruments whose envelopes it
        shortened.
        """
        paragraphs: List[str] = [self._message(EXPORT_PROJECT_ELEMENTS[export_format].exported_message)]
        for notice in (
            self._skipped_row_messages.notice(skipped_rows, self._project_manager.current.voices),
            self._truncation_messages.notice(truncation),
        ):
            if notice is not None:
                paragraphs.append(notice)

        return "\n\n".join(paragraphs)

    def _guard_open(
        self,
        *,
        title: GlobalDialogTitleElements,
        message: GlobalMessageElements,
        open_message: GlobalMessageElements,
        proceed: VoidCallback,
        decline: VoidCallback,
    ) -> None:
        """Lets another project take the open one's place, asking first while one is open.

        Unsaved changes are offered a save, and an open project holding none is still asked about,
        so a project is replaced only by an answer. Cancel turns the request away.
        """
        if not self._project_controller.is_open:
            proceed()
            return

        if self.is_unsaved:
            self._dialogs.show_save_confirmation(
                tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
                title=self._title(title),
                message=self._message(message),
                on_save=self._write_project,
                on_confirm=proceed,
                on_cancel=decline,
                ok_label=self._label(DialogElements.DISCARD),
            )
        else:
            self._dialogs.show_confirmation(
                tag=TAG_GLOBAL_DIALOG_PROJECT_OPEN,
                title=self._title(title),
                message=self._message(open_message),
                on_confirm=proceed,
                on_cancel=decline,
                ok_label=self._label(DialogElements.DISCARD),
            )

    def _title(self, element: GlobalDialogTitleElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            element,
        ]

    def _message(self, element: GlobalMessageElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            element,
        ]

    def _label(self, element: DialogElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            element,
        ]

    def _filter_name(self, element: FileFilterElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.FILTER,
            element,
        ]
