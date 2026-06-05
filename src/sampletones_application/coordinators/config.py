from pathlib import Path

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    GlobalDialogTitleElements,
    GlobalMessageElements,
)
from sampletones_application.categories.elements.reconstructions import ReconstructionPanelElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.application.manager import SessionManager
from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import TAG_GLOBAL_DIALOG_CONFIG_STATUS
from sampletones_application.layout import LayoutConfig
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.file import file_dialog_handler
from sampletones_core.paths import EXT_FILE_JSON
from sampletones_shared.logger import logger


class ConfigCoordinator:
    def __init__(
        self,
        config_manager: ConfigManager,
        session_manager: SessionManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
        layout: LayoutConfig,
    ) -> None:
        self._config_manager = config_manager
        self._session_manager = session_manager
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._layout = layout

    def save_dialog(self) -> None:
        with dpg.file_dialog(
            label=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.SAVE_CONFIG,
            ],
            width=self._layout.general.dialogs.file.width,
            height=self._layout.general.dialogs.file.height,
            callback=self._handle_save,
            file_count=1,
            default_filename="config",
            default_path=str(self._session_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_save(self, filepath: Path) -> None:
        try:
            self._config_manager.save_config_to_file(filepath)
            self._show_status_dialog(
                self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.CONFIGURATION_SAVED_SUCCESSFULLY,
                ]
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to save config to {filepath}")
            self._dialogs.show_error(
                exception,
                self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.CONFIG_SAVE_FAILED,
                ],
            )

        self._session_manager.set_config_path(filepath)

    def load_dialog(self) -> None:
        with dpg.file_dialog(
            label=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.LOAD_CONFIG,
            ],
            width=self._layout.general.dialogs.file.width,
            height=self._layout.general.dialogs.file.height,
            callback=self._handle_load,
            file_count=1,
            default_path=str(self._session_manager.get_config_path()),
        ):
            dpg.add_file_extension(EXT_FILE_JSON)

    @file_dialog_handler
    def _handle_load(self, filepath: Path) -> None:
        try:
            self._config_manager.load_config_from_file(filepath)
            self._show_status_dialog(
                self._language_manager[
                    Page.GLOBAL,
                    Panel.DIALOG,
                    TextType.MESSAGE,
                    GlobalMessageElements.CONFIGURATION_LOADED_SUCCESSFULLY,
                ]
            )
        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback(exception, f"Failed to load config from {filepath}")
            self._dialogs.show_error(
                exception,
                self._language_manager[
                    Page.RECONSTRUCTIONS,
                    Panel.RECONSTRUCTION,
                    TextType.MESSAGE,
                    ReconstructionPanelElements.EXPORT_WAV_FAILED,
                ],
            )

        self._session_manager.set_config_path(filepath)

    def _show_status_dialog(self, message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(message, parent=parent)

        self._dialogs.show_modal(
            tag=TAG_GLOBAL_DIALOG_CONFIG_STATUS,
            title=self._language_manager[
                Page.GLOBAL,
                Panel.DIALOG,
                TextType.TITLE,
                GlobalDialogTitleElements.CONFIG_STATUS,
            ],
            content=content,
        )
