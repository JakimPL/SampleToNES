from pathlib import Path
from typing import Dict, Optional

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.elements.global_ import (
    DialogElements,
    FileFilterElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.categories.trackers import TRACKER_PROJECT_ELEMENTS
from sampletones_application.config.managers.session import SessionManager
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
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.paths import EXT_FILE_PROJECT
from sampletones_core.trackers.backend import TrackerBackend
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.scope import ExportScope
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
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.system.paths import get_directory


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
        tracker_backends: Dict[TrackerFormat, TrackerBackend],
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        on_tab_switch: Callback,
        on_session_state_changed: VoidCallback,
    ) -> None:
        self._project_controller = project_controller
        self._project_manager = project_manager
        self._session_manager = session_manager
        self._export_service = export_service
        self._tracker_backends = tracker_backends
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._on_tab_switch = on_tab_switch
        self._project_manager.session.on_state_changed = on_session_state_changed

        export_service.subscribe(self._on_export_result)

    @property
    def project_name(self) -> Optional[str]:
        name = self._project_manager.session.name
        return name or None

    @property
    def is_unsaved(self) -> bool:
        return self._project_controller.is_dirty

    def new_project_with_confirmation(self) -> None:
        self._guard_open(
            title=GlobalDialogTitleElements.NEW_UNSAVED_PROJECT,
            message=GlobalMessageElements.NEW_UNSAVED_PROJECT,
            open_message=GlobalMessageElements.NEW_OPEN_PROJECT,
            on_confirm=self._new,
        )

    def open_with_confirmation(self, filepath: Optional[Path] = None) -> None:
        def open_project() -> None:
            if filepath is None:
                self._open_dialog()
            else:
                self._load(filepath)

        self._guard_open(
            title=GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT,
            message=GlobalMessageElements.OPEN_UNSAVED_PROJECT,
            open_message=GlobalMessageElements.OPEN_OPEN_PROJECT,
            on_confirm=open_project,
        )

    def load_project_safely(self, path: Path) -> None:
        """Loads the persisted project when the application starts.

        Startup restore happens automatically, so a failed load is recovered silently:
        the stale session pointer is cleared so a missing, moved, or corrupt file leaves
        the next launch starting from a clean slate. Only known domain and I/O failures
        are absorbed; unexpected errors propagate.
        """
        try:
            self._project_controller.load(path)
        except (SampleToNESError, OSError) as exception:
            logger.warning(f"Could not restore project from {logger.format_path(path)}: {exception}")
            self._session_manager.set_current_project(None)

    def close_with_confirmation(self) -> None:
        if not self._project_controller.is_open:
            return

        if self.is_unsaved:
            self._dialogs.show_save_confirmation(
                tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
                title=self._title(GlobalDialogTitleElements.CLOSE_UNSAVED_PROJECT),
                message=self._message(GlobalMessageElements.CLOSE_UNSAVED_PROJECT),
                on_save=self.save,
                on_confirm=self._close,
                ok_label=self._label(DialogElements.DISCARD),
            )
        else:
            self._close()

    def show_exit_save_confirmation(self, on_confirm: VoidCallback) -> None:
        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
            title=self._title(GlobalDialogTitleElements.EXIT_CONFIRMATION),
            message=self._message(GlobalMessageElements.EXIT_UNSAVED_PROJECT),
            on_save=self.save,
            on_confirm=on_confirm,
            ok_label=self._label(DialogElements.EXIT),
        )

    def save(self) -> bool:
        """Saves the project to its current file, prompting for one when it has none.

        Reports whether the project was written, so a caller waiting on the save (the exit and
        close prompts) proceeds only once it lands on disk and holds when the user cancels.
        """
        filepath = self._session_manager.current_project
        if filepath is None:
            return self.save_as_dialog()

        return self._save(filepath)

    def save_as_dialog(self) -> bool:
        """Prompts for a destination and saves the project there, reporting whether it was written."""
        path = self._session_manager.get_project_path()
        filename = path.name if path.is_file() else DEFAULT_PROJECT_FILENAME
        directory = get_directory(path)
        filepath = save_file_dialog(
            title=self._title(GlobalDialogTitleElements.SAVE_PROJECT),
            initial_directory=directory,
            default_filename=filename,
            extensions=[EXT_FILE_PROJECT],
            filter_name=self._filter_name(FileFilterElements.PROJECT),
        )

        return self._handle_save_as(filepath)

    def _get_project_filename(self, extension: str) -> str:
        name = self.project_name or DEFAULT_EXPORT_NAME
        return f"{name}{extension}"

    def export_project_dialog(self, tracker_format: TrackerFormat) -> None:
        """Prompts for a destination and writes the open project in ``tracker_format``.

        Args:
            tracker_format: The tracker the project is written for.
        """
        if not self._project_controller.is_open:
            return

        backend = self._tracker_backends[tracker_format]
        elements = TRACKER_PROJECT_ELEMENTS[tracker_format]
        extension = backend.extension(ExportScope.PROJECT)
        path = self._session_manager.get_project_path()
        filepath = save_file_dialog(
            title=self._title(elements.dialog_title),
            initial_directory=get_directory(path),
            default_filename=self._get_project_filename(extension),
            extensions=[extension],
            filter_name=self._filter_name(elements.filter_name),
        )

        self._handle_export_project(filepath, tracker_format)

    def _open_dialog(self) -> None:
        filepath = open_file_dialog(
            title=self._title(GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT),
            initial_directory=self._session_manager.get_project_path(),
            extensions=[EXT_FILE_PROJECT],
            filter_name=self._filter_name(FileFilterElements.PROJECT),
        )

        self._handle_open(filepath)

    @ignore_none_path
    def _handle_open(self, filepath: Path) -> None:
        self._session_manager.set_project_path(filepath.parent)
        self._load(filepath)

    @ignore_none_path(default=False)
    def _handle_save_as(self, filepath: Path) -> bool:
        self._session_manager.set_project_path(filepath.parent)
        return self._save(filepath)

    @ignore_none_path
    def _handle_export_project(self, filepath: Path, tracker_format: TrackerFormat) -> None:
        self._export_service.export_project(
            filepath,
            self._tracker_backends[tracker_format],
            self._project_controller.export_request,
        )

    def _new(self) -> None:
        self._project_controller.new()
        self._session_manager.set_current_project(None)
        self._on_tab_switch(Tab.SEQUENCER)

    def _close(self) -> None:
        self._project_controller.close()
        self._session_manager.set_current_project(None)

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

        self._session_manager.set_current_project(filepath)
        self._on_tab_switch(Tab.SEQUENCER)

    def _save(self, filepath: Path) -> bool:
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
            return False

        self._session_manager.set_current_project(filepath)
        self._dialogs.show_info(
            TAG_GLOBAL_DIALOG_PROJECT_SAVED,
            self._message(GlobalMessageElements.PROJECT_SAVED_SUCCESSFULLY),
            self._title(GlobalDialogTitleElements.PROJECT_SAVED),
        )
        return True

    def _on_export_result(self, result: ExportResult) -> None:
        """Reports a finished project export in the words of the format it was written in."""
        match result:
            case ExportSuccess(
                kind=ExportKind.PROJECT,
                tracker_format=TrackerFormat() as tracker_format,
            ):
                self._dialogs.show_info(
                    TAG_GLOBAL_DIALOG_MODULE_EXPORTED,
                    self._message(TRACKER_PROJECT_ELEMENTS[tracker_format].exported_message),
                    self._title(GlobalDialogTitleElements.PROJECT_EXPORTED),
                )
            case ExportError(
                kind=ExportKind.PROJECT,
                tracker_format=TrackerFormat() as tracker_format,
                exception=exception,
            ):
                self._dialogs.show_error(
                    exception,
                    self._message(TRACKER_PROJECT_ELEMENTS[tracker_format].export_failed_message),
                )

    def _guard_open(
        self,
        *,
        title: AbstractElement,
        message: AbstractElement,
        open_message: AbstractElement,
        on_confirm: Callback,
    ) -> None:
        if not self._project_controller.is_open:
            on_confirm()
            return

        if self.is_unsaved:
            self._dialogs.show_save_confirmation(
                tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
                title=self._title(title),
                message=self._message(message),
                on_save=self.save,
                on_confirm=on_confirm,
                ok_label=self._label(DialogElements.DISCARD),
            )
        else:
            self._dialogs.show_confirmation(
                tag=TAG_GLOBAL_DIALOG_PROJECT_OPEN,
                title=self._title(title),
                message=self._message(open_message),
                on_confirm=on_confirm,
                ok_label=self._label(DialogElements.DISCARD),
            )

    def _title(self, element: AbstractElement) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TITLE,
            element,
        ]

    def _message(self, element: AbstractElement) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            element,
        ]

    def _label(self, element: AbstractElement) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.LABEL,
            element,
        ]

    def _filter_name(self, element: AbstractElement) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.FILTER,
            element,
        ]
