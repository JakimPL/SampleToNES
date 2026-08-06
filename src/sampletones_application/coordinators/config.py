import json
from pathlib import Path
from typing import Dict, Final, Tuple

import dearpygui.dearpygui as dpg
from pydantic import ValidationError

from sampletones_application.categories.elements.global_ import GlobalMessageElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.config.managers.outcome import (
    ConfigLoadFailure,
    ConfigLoadFailureReason,
    ConfigRecovered,
)
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.tags.general import (
    TAG_GLOBAL_DIALOG_CONFIG_RECOVERY,
    TAG_GLOBAL_DIALOG_CONFIG_STATUS,
)
from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.result import ignore_none_path
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_core.paths import EXT_FILE_JSON
from sampletones_shared.application import SAMPLETONES_VERSION
from sampletones_shared.logger import logger
from sampletones_shared.utils.validation import flatten_location

_LOAD_FAILURE_MESSAGES: Dict[ConfigLoadFailureReason, GlobalMessageElements] = {
    ConfigLoadFailureReason.LOAD_ERROR: GlobalMessageElements.CONFIGURATION_LOAD_ERROR,
    ConfigLoadFailureReason.PARSE_ERROR: GlobalMessageElements.CONFIGURATION_PARSE_ERROR,
    ConfigLoadFailureReason.INVALID: GlobalMessageElements.CONFIGURATION_INVALID_ERROR,
}

_LOAD_EXCEPTIONS = (
    OSError,
    json.JSONDecodeError,
    UnicodeDecodeError,
    TypeError,
    ValidationError,
)

DEFAULT_CONFIG_FILENAME: Final[str] = "config"


class ConfigCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._dialogs = dialogs
        self._language_manager = language_manager

    def save_dialog(self) -> None:
        filepath = save_file_dialog(
            title=self._language_manager["global.dialog.title.save_config"],
            initial_directory=self._session_manager.get_config_path(),
            default_filename=DEFAULT_CONFIG_FILENAME,
            filters=self._config_filters(),
        )

        self._handle_save(filepath)

    @ignore_none_path
    def _handle_save(self, filepath: Path) -> None:
        try:
            self._config_manager.save_config_to_file(filepath)
            self._show_status_dialog(self._language_manager["global.dialog.message.configuration_saved_successfully"])
        except (OSError, ValueError) as exception:
            logger.error_with_traceback(exception, f"Failed to save config to {filepath}")
            self._dialogs.show_error(
                exception,
                self._language_manager["global.dialog.message.config_save_failed"],
            )

        self._session_manager.set_config_path(filepath)

    def load_dialog(self) -> None:
        filepath = open_file_dialog(
            title=self._language_manager["global.dialog.title.load_config"],
            initial_directory=self._session_manager.get_config_path(),
            filters=self._config_filters(),
        )

        self._handle_load(filepath)

    def _config_filters(self) -> Tuple[FileFilter, ...]:
        """The single type a configuration is written as and read from."""
        return (
            FileFilter.for_extensions(
                self._language_manager["global.dialog.filter.config"],
                [EXT_FILE_JSON],
            ),
        )

    @ignore_none_path
    def _handle_load(self, filepath: Path) -> None:
        try:
            self._config_manager.load_config_from_file(filepath)
            self.present_pending_load_outcomes()
            self._show_status_dialog(self._message(GlobalMessageElements.CONFIGURATION_LOADED_SUCCESSFULLY))
        except _LOAD_EXCEPTIONS as exception:
            logger.error_with_traceback(exception, f"Failed to load config from {filepath}")
            self._dialogs.show_error(
                exception,
                self._message(GlobalMessageElements.CONFIGURATION_LOAD_ERROR),
            )

        self._session_manager.set_config_path(filepath)

    def present_pending_load_outcomes(self) -> None:
        """
        Presents the outcomes the config manager recorded while loading, then clears them.

        The manager loads its configuration during construction, before the GUI exists, so it
        records each recovery or failure as data. This coordinator, once a window can be drawn,
        turns each outcome into the matching dialog with text from the language manager.
        """
        for outcome in self._config_manager.pending_load_outcomes:
            match outcome:
                case ConfigRecovered(source_version=source_version, dropped=dropped):
                    properties = tuple(
                        flatten_location(location)
                        for location in sorted(
                            dropped,
                            key=flatten_location,
                        )
                    )
                    self._dialogs.show_config_recovery(
                        tag=TAG_GLOBAL_DIALOG_CONFIG_RECOVERY,
                        source_version=source_version,
                        target_version=SAMPLETONES_VERSION,
                        properties=properties,
                        config_path=self._config_manager.config_path,
                    )
                case ConfigLoadFailure(exception=exception, reason=reason):
                    self._dialogs.show_error(
                        exception,
                        self._message(_LOAD_FAILURE_MESSAGES[reason]),
                    )

        self._config_manager.pending_load_outcomes.clear()

    def _message(self, element: GlobalMessageElements) -> str:
        return self._language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            element,
        ]

    def _show_status_dialog(self, message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        self._dialogs.show_modal(
            tag=TAG_GLOBAL_DIALOG_CONFIG_STATUS,
            title=self._language_manager["global.dialog.title.config_status"],
            content=content,
        )
