from pathlib import Path

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
    LoadReconstructionError,
)
from sampletones_shared.logger import logger


class ReconstructionLoading:
    """Opens a reconstruction file, reporting each way a load fails in words of its own.

    A failure outside the load contract is a bug, so it propagates.
    """

    def __init__(
        self,
        reconstruction_manager: ReconstructionManager,
        *,
        dialogs: DialogsRenderer,
        language_manager: LanguageManager,
    ) -> None:
        self._reconstruction_manager = reconstruction_manager
        self._dialogs = dialogs
        self._language_manager = language_manager
        self._msg_load_error = language_manager["reconstructions.browser.message.load_error"]

    def load(self, filepath: Path) -> None:
        try:
            self._reconstruction_manager.load_reconstruction(filepath)
            logger.info(f"Loaded reconstruction: {logger.format_path(filepath)}")
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction data from {filepath}")
            self._dialogs.show_file_not_found(
                filepath,
                self._language_manager["reconstructions.browser.message.file_not_found"],
            )
        except (IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error while loading reconstruction data from {filepath}")
            self._dialogs.show_error(exception, self._msg_load_error)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in the reconstruction file {filepath}")
            self._dialogs.show_error(exception, self._language_manager["global.dialog.message.invalid_metadata_error"])
        except InvalidReconstructionValuesError as exception:
            logger.error_with_traceback(exception, f"Reconstruction contains invalid values: {filepath}")
            self._dialogs.show_error(
                exception, self._language_manager["reconstructions.browser.message.invalid_values"]
            )
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(exception, f"Invalid reconstruction file: {filepath}")
            self._dialogs.show_error(exception, self._language_manager["reconstructions.browser.message.invalid_file"])
        except IncompatibleReconstructionVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible reconstruction version: {exception.actual_version}"
                f" != expected {exception.expected_version}",
            )
            self._dialogs.show_error(
                exception,
                self._language_manager["reconstructions.browser.template.incompatible_version_template"].format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception, f"Deserialization error while loading reconstruction from {filepath}"
            )
            self._dialogs.show_error(
                exception,
                self._language_manager["reconstructions.browser.message.deserialization_error"],
            )
        except LoadReconstructionError as exception:
            logger.error_with_traceback(
                exception,
                f"Unhandled load error while loading reconstruction data from {filepath}",
            )
            self._dialogs.show_error(exception, self._msg_load_error)
