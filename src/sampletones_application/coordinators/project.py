from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.categories.elements.global_ import (
    DialogElements,
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, Tab, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    TAG_GLOBAL_DIALOG_PROJECT_SAVED,
    TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
)
from sampletones_application.layout import LayoutConfig
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.file import file_dialog_handler
from sampletones_core.paths import EXT_FILE_PROJECT
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import Callback


class ProjectCoordinator:
    """Drives project file operations from the menu and keyboard shortcuts.

    Mirrors :class:`ReconstructionCoordinator` for the project document: it owns
    the new/open/save/save-as/close flow, guards unsaved changes, and routes every
    mutation through the :class:`ProjectController`. The application always holds a
    project (an empty one on startup), so these operations are always available;
    "close" simply reverts to a fresh empty project.
    """

    def __init__(
        self,
        project_controller: ProjectController,
        project_manager: ProjectManager,
        session_manager: SessionManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        layout: LayoutConfig,
        on_tab_switch: Callback,
    ) -> None:
        self._project_controller = project_controller
        self._project_manager = project_manager
        self._session_manager = session_manager
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._layout = layout
        self._on_tab_switch = on_tab_switch

    @property
    def is_unsaved(self) -> bool:
        return self._project_manager.is_dirty

    def new_with_confirmation(self) -> None:
        self._guard_unsaved(
            title=GlobalDialogTitleElements.NEW_UNSAVED_PROJECT,
            message=GlobalMessageElements.NEW_UNSAVED_PROJECT,
            on_confirm=self._new,
        )

    def open_with_confirmation(self, filepath: Optional[Path] = None) -> None:
        def open_project() -> None:
            if filepath is None:
                self._open_dialog()
            else:
                self._load(filepath)

        self._guard_unsaved(
            title=GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT,
            message=GlobalMessageElements.OPEN_UNSAVED_PROJECT,
            on_confirm=open_project,
        )

    def close_with_confirmation(self) -> None:
        self._guard_unsaved(
            title=GlobalDialogTitleElements.CLOSE_UNSAVED_PROJECT,
            message=GlobalMessageElements.CLOSE_UNSAVED_PROJECT,
            on_confirm=self._close,
        )

    def save(self) -> None:
        filepath = self._session_manager.current_project
        if filepath is None:
            self.save_as_dialog()
        else:
            self._save(filepath)

    def save_as_dialog(self) -> None:
        with dpg.file_dialog(
            label=self._title(GlobalDialogTitleElements.SAVE_PROJECT),
            width=self._layout.general.dialogs.file.width,
            height=self._layout.general.dialogs.file.height,
            callback=self._handle_save_as,
            file_count=1,
            default_path=str(self._session_manager.get_project_path()),
        ):
            dpg.add_file_extension(EXT_FILE_PROJECT)

    def _open_dialog(self) -> None:
        with dpg.file_dialog(
            label=self._title(GlobalDialogTitleElements.OPEN_UNSAVED_PROJECT),
            width=self._layout.general.dialogs.file.width,
            height=self._layout.general.dialogs.file.height,
            callback=self._handle_open,
            file_count=1,
            default_path=str(self._session_manager.get_project_path()),
        ):
            dpg.add_file_extension(EXT_FILE_PROJECT)

    @file_dialog_handler
    def _handle_open(self, filepath: Path) -> None:
        self._session_manager.set_project_path(filepath.parent)
        self._load(filepath)

    @file_dialog_handler
    def _handle_save_as(self, filepath: Path) -> None:
        self._session_manager.set_project_path(filepath.parent)
        self._save(filepath)

    def _new(self) -> None:
        self._project_controller.new()
        self._session_manager.set_current_project(None)
        self._on_tab_switch(Tab.SEQUENCER)

    def _close(self) -> None:
        self._project_controller.new()
        self._session_manager.set_current_project(None)

    def _load(self, filepath: Path) -> None:
        try:
            self._project_controller.load(filepath)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to load project from {filepath}")
            self._dialogs.show_error(exception)
            return

        self._session_manager.set_current_project(filepath)
        self._on_tab_switch(Tab.SEQUENCER)

    def _save(self, filepath: Path) -> None:
        try:
            self._project_controller.save(filepath)
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save project to {filepath}")
            self._dialogs.show_error(
                exception,
                self._message(GlobalMessageElements.PROJECT_SAVE_FAILED),
            )
            return

        self._session_manager.set_current_project(filepath)
        self._dialogs.show_info(
            TAG_GLOBAL_DIALOG_PROJECT_SAVED,
            self._message(GlobalMessageElements.PROJECT_SAVED_SUCCESSFULLY),
            self._title(GlobalDialogTitleElements.PROJECT_SAVED),
        )

    def _guard_unsaved(
        self,
        *,
        title: AbstractElement,
        message: AbstractElement,
        on_confirm: Callback,
    ) -> None:
        if not self.is_unsaved:
            on_confirm()
            return

        self._dialogs.show_save_confirmation(
            tag=TAG_GLOBAL_DIALOG_PROJECT_UNSAVED,
            title=self._title(title),
            message=self._message(message),
            on_save=self.save,
            on_confirm=on_confirm,
            ok_label=self._label(DialogElements.DISCARD),
        )

    def _title(self, element: AbstractElement) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.TITLE, element]

    def _message(self, element: AbstractElement) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.MESSAGE, element]

    def _label(self, element: AbstractElement) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]
