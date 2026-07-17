import threading
from pathlib import Path
from typing import Callable, Optional

from sampletones_application.categories.elements.global_ import (
    GlobalMessageElements,
    GlobalTemplateElements,
)
from sampletones_application.categories.elements.instructions import (
    InstructionsLibraryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.view_model.instruction.library import (
    LibraryPanelViewModel,
)
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.generators import (
    GENERATOR_CLASS_MAP,
    GENERATOR_TO_INSTRUCTION_MAP,
    LIBRARY_GENERATOR_CLASS_MAP,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import (
    InstructionLibraryKey,
    get_display_name_from_key,
)
from sampletones_core.library.filename.utils import create_key_from_filename
from sampletones_core.parallelization import (
    ETAEstimator,
    TaskProgress,
    TaskStatus,
)
from sampletones_core.structures.tree import Tree
from sampletones_shared.exceptions import (
    DeserializationError,
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    LoadLibraryError,
    WindowNotAvailableError,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.filesystem import remove_path

OnLoadInstructionCallback = Callable[[InstructionUnion], None]
OnApplyLibraryConfigCallback = Callable[[InstructionLibraryKey], None]


class LibraryLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        *,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._config_manager = config_manager
        self._library_manager = library_manager
        self._is_operation_active = is_operation_active
        self._eta_estimator: Optional[ETAEstimator] = None
        self._status_lock = threading.Lock()

        self._lock_function: Optional[VoidCallback] = None
        self._unlock_function: Optional[VoidCallback] = None
        self._is_locked_function: Optional[Callable[[], bool]] = None

        self.on_rebuild_tree_needed: Optional[VoidCallback] = None
        self.on_generation_state_changed: Optional[VoidCallback] = None
        self.on_view_changed: Optional[Callable[[LibraryPanelViewModel], None]] = None
        self.on_instruction_loaded: Optional[OnLoadInstructionCallback] = None
        self.on_apply_library_config: Optional[OnApplyLibraryConfigCallback] = None
        self.on_generation_completed: Optional[VoidCallback] = None
        self.on_generation_error: Optional[Callable[[Exception], None]] = None
        self.on_generation_cancelled: Optional[VoidCallback] = None
        self.on_load_file_not_found: Optional[Callable[[Path, str], None]] = None
        self.on_load_error: Optional[Callable[[Exception, str], None]] = None

        self._lbl_generate_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.GENERATE_LIBRARY_BUTTON,
        ]
        self._lbl_regenerate_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.REGENERATE_LIBRARY_BUTTON,
        ]
        self._msg_invalid_metadata_error = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.INVALID_METADATA_ERROR,
        ]
        self._msg_generating = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATING,
        ]
        self._msg_generation_saving = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_SAVING,
        ]
        self._msg_generation_failed = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_FAILED,
        ]
        self._msg_generation_cancelled = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_CANCELLED,
        ]
        self._msg_window_not_available = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_WINDOW_NOT_AVAILABLE,
        ]
        self._msg_load_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_LOAD_ERROR,
        ]
        self._msg_invalid_data_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_INVALID_DATA,
        ]
        self._msg_invalid_data_values_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_INVALID_DATA_VALUES,
        ]
        self._msg_deserialization_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_DESERIALIZATION_ERROR,
        ]
        self._msg_file_not_found = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_FILE_NOT_FOUND,
        ]
        self._msg_file_load_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_FILE_LOAD_ERROR,
        ]
        self._tpl_time_estimation = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.TIME_ESTIMATION,
        ]
        self._tpl_generation_progress = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TEMPLATE,
            InstructionsLibraryElements.GENERATION_PROGRESS_TEMPLATE,
        ]
        self._tpl_incompatible_version_error = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TEMPLATE,
            InstructionsLibraryElements.INCOMPATIBLE_VERSION_TEMPLATE,
        ]
        self._tpl_not_exists = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TEMPLATE,
            InstructionsLibraryElements.LIBRARY_NOT_EXISTS_TEMPLATE,
        ]
        self._tpl_library_exists = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TEMPLATE,
            InstructionsLibraryElements.LIBRARY_EXISTS_TEMPLATE,
        ]
        self._tpl_library_loaded = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TEMPLATE,
            InstructionsLibraryElements.LIBRARY_LOADED_TEMPLATE,
        ]

        self._library_manager.set_callbacks(
            on_generation_start=self._on_generation_start,
            on_generation_progress=self._on_generation_progress,
            on_generation_completed=self._on_generation_completed,
            on_generation_error=self._on_generation_error,
            on_generation_cancelled=self._on_generation_cancelled,
        )

    def configure_lock(
        self,
        lock_function: VoidCallback,
        unlock_function: VoidCallback,
        is_locked_function: Callable[[], bool],
    ) -> None:
        self._lock_function = lock_function
        self._unlock_function = unlock_function
        self._is_locked_function = is_locked_function

    def _do_lock(self) -> None:
        if self._lock_function is not None:
            self._lock_function()

    def _do_unlock(self) -> None:
        if self._unlock_function is not None:
            self._unlock_function()

    @property
    def _is_locked(self) -> bool:
        if self._is_locked_function is not None:
            return self._is_locked_function()

        return False

    @property
    def tree(self) -> Tree:
        return self._library_manager.tree

    @property
    def config_key(self) -> InstructionLibraryKey:
        return self._config_manager.key

    @property
    def current_library_key(self) -> Optional[InstructionLibraryKey]:
        return self._library_manager.current_library_key

    def is_library_generating(self) -> bool:
        return self._library_manager.is_generating()

    def library_available_for_config(self) -> bool:
        return self._library_manager.is_library_available_for_config()

    def is_library_loaded(self, key: InstructionLibraryKey) -> bool:
        return self._library_manager.is_library_loaded(key)

    def library_exists_for_key(self, key: InstructionLibraryKey) -> bool:
        return self._library_manager.library_exists_for_key(key)

    def get_path(self, key: InstructionLibraryKey) -> Path:
        return self._library_manager.get_path(key)

    def rebuild_tree(self) -> None:
        self._library_manager.rebuild_tree()

    def refresh_libraries(self, load_if_needed: bool = True) -> None:
        self._library_manager.set_library_directory(self._config_manager.get_library_directory())
        self._library_manager.gather_available_libraries()
        self._sync_with_config_key(load_if_needed=load_if_needed)
        self.call(self.on_rebuild_tree_needed)

    def remove_library(self, library_key: InstructionLibraryKey) -> Path:
        filepath = self._library_manager.get_path(library_key)
        remove_path(filepath)

        if self.current_library_key == library_key:
            self._library_manager.clear_current_library()

        self.refresh_libraries(load_if_needed=False)
        return filepath

    def update_status(self) -> None:
        """Repaints the idle library status; during a generation the progress handlers own the
        emission stream, so this call yields to them."""
        if self._library_manager.is_generating():
            return

        self._emit_view()

    def load_library_file(self, filepath: Path) -> None:
        if self._is_locked:
            logger.warning("Library is already loading; please wait until it finishes")
            return

        try:
            library_key = create_key_from_filename(filepath.name)
        except ValueError as exception:
            logger.error_with_traceback(exception, f"Invalid library file name format: {filepath.name}")
            self.call(self.on_load_error, exception, self._msg_load_error)
            return

        self.load_library_and_set_current(library_key)
        self.update_status()

    def load_generator(self, library_generator_name: LibraryGeneratorName) -> None:
        if self._is_locked:
            return

        generator_class = GENERATOR_CLASS_MAP[LIBRARY_GENERATOR_CLASS_MAP[library_generator_name]]
        instruction_class = GENERATOR_TO_INSTRUCTION_MAP[generator_class]
        instruction = instruction_class.default_instruction()
        self.load_instruction(instruction)

    def load_instruction(self, instruction: InstructionUnion) -> None:
        if self._is_locked:
            return

        self._do_lock()
        try:
            instruction_data = self._library_manager.load_instruction(instruction)
            self.call(self.on_instruction_loaded, instruction_data)
        finally:
            self._do_unlock()
            self.update_status()

    def request_generation(self) -> None:
        """Starts a user-requested library generation, the exclusive-operation gate permitting.

        The Generate button routes here so a standalone generation yields to an in-flight conversion.
        A conversion's own preparatory generation calls :meth:`generate_library` directly, past the
        gate, since it is part of the active operation."""
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress")
            return

        self.generate_library()

    def generate_library(self) -> None:
        if self._library_manager.is_generating():
            return

        config = self._config_manager.config
        window = self._config_manager.window

        if not window:
            exception = WindowNotAvailableError(self._msg_window_not_available)
            logger.info("No FFT window available for library generation")
            self.call(self.on_load_error, exception, self._msg_window_not_available)
            return

        self._library_manager.generate_library(config, window)
        self._emit_view(self._msg_generating)

    def cancel_generation(self) -> None:
        self._library_manager.cancel_generation()

    def _sync_with_config_key(self, load_if_needed: bool = True) -> None:
        config_key = self._config_manager.key
        matching_key = self._library_manager.sync_with_config_key(config_key)
        if matching_key:
            self._set_current_library(matching_key, load_if_needed=load_if_needed, apply_config=False)

    def _set_current_library(
        self,
        library_key: InstructionLibraryKey,
        load_if_needed: bool = True,
        apply_config: bool = False,
    ) -> None:
        if load_if_needed and not self._library_manager.is_library_loaded(library_key):
            self._load_library(library_key)

        if apply_config:
            self.call(self.on_apply_library_config, library_key)

        self.update_status()

    def load_library_and_set_current(self, library_key: InstructionLibraryKey) -> None:
        self._set_current_library(library_key, load_if_needed=True, apply_config=True)

    def _load_library(self, library_key: InstructionLibraryKey) -> None:
        if self._is_locked:
            return

        self._do_lock()
        try:
            self._library_manager.load_library(library_key)
            logger.info(f"Library loaded: {library_key}")
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Library file not found for key {library_key}")
            self.call(
                self.on_load_file_not_found,
                self._library_manager.get_path(library_key),
                self._msg_file_not_found,
            )
        except (
            IOError,
            IsADirectoryError,
            PermissionError,
            OSError,
        ) as exception:
            logger.error_with_traceback(exception, f"Error loading library file for key {library_key}")
            self.call(self.on_load_error, exception, self._msg_file_load_error)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(
                exception,
                f"Invalid metadata in library file for key {library_key}",
            )
            self.call(self.on_load_error, exception, self._msg_invalid_metadata_error)
        except InvalidLibraryDataValuesError as exception:
            logger.error_with_traceback(
                exception,
                f"Library data contains invalid values for key {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._msg_invalid_data_values_error,
            )
        except InvalidLibraryDataError as exception:
            logger.error_with_traceback(exception, f"Invalid library data file for {library_key}")
            self.call(self.on_load_error, exception, self._msg_invalid_data_error)
        except IncompatibleLibraryDataVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible library data version for key {library_key}: "
                f"{exception.actual_version} != expected {exception.expected_version}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._tpl_incompatible_version_error.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception,
                f"Deserialization error loading library for key {library_key}",
            )
            self.call(self.on_load_error, exception, self._msg_deserialization_error)
        except LoadLibraryError as exception:
            logger.error_with_traceback(exception, f"Error loading library for key {library_key}")
            self.call(self.on_load_error, exception, self._msg_load_error)
        finally:
            self._do_unlock()

    def _on_generation_start(self) -> None:
        self._do_lock()
        assert self._library_manager.creator is not None, "Library manager creator is not initialized"
        self._eta_estimator = ETAEstimator(self._library_manager.creator.total_instructions)
        self.call(self.on_generation_state_changed)

    def _on_generation_progress(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        with self._status_lock:
            match task_status:
                case TaskStatus.COMPLETED:
                    self._emit_view(self._msg_generation_saving, progress=1.0)
                case TaskStatus.FAILED:
                    self._emit_view(self._msg_generation_failed)
                case TaskStatus.CANCELLED:
                    self._emit_view(self._msg_generation_cancelled)
                case TaskStatus.RUNNING:
                    self._update_progress_state(task_progress)

    def _update_progress_state(self, task_progress: TaskProgress) -> None:
        creator = self._library_manager.creator
        assert creator is not None, "Library manager creator is not initialized"
        assert self._eta_estimator is not None, "ETA Estimator is not initialized"

        eta_seconds = self._eta_estimator.update(creator.completed_instructions)
        eta_string = ETAEstimator.format_duration(eta_seconds)

        status_text = self._tpl_generation_progress.format(
            creator.completed_instructions,
            creator.total_instructions,
        )
        if eta_string:
            status_text += self._tpl_time_estimation.format(eta_string=eta_string)

        self._emit_view(status_text, progress=task_progress.get_progress())

    def _on_generation_completed(self) -> None:
        self.call(self.on_generation_completed)
        self._finalize_generation()

    def _on_generation_error(self, exception: Exception) -> None:
        self.call(self.on_generation_error, exception)
        self._finalize_generation_error()

    def _on_generation_cancelled(self) -> None:
        self.call(self.on_generation_cancelled)
        self._finalize_generation()

    def _finalize_generation(self) -> None:
        try:
            self._library_manager.cleanup_creator()
            self._set_current_library(
                self._config_manager.key,
                load_if_needed=True,
                apply_config=False,
            )
            self.refresh_libraries()
        finally:
            self._do_unlock()
            self.call(self.on_generation_state_changed)

    def _finalize_generation_error(self) -> None:
        try:
            self._library_manager.cleanup_creator()
            self.update_status()
        finally:
            self._do_unlock()
            self.call(self.on_generation_state_changed)

    def _emit_view(self, status_text: Optional[str] = None, *, progress: float = 0.0) -> None:
        """Builds and emits the panel view model from freshly computed values.

        ``status_text`` of ``None`` renders the idle status derived from the manager state;
        generation emits pass their status and progress explicitly.
        """
        key = self._config_manager.key
        is_generating = self._library_manager.is_generating()

        if status_text is None:
            library_name = get_display_name_from_key(key)
            if self._library_manager.is_library_loaded(key):
                status_text = self._tpl_library_loaded.format(library_name)
            elif self._library_manager.library_exists_for_key(key):
                status_text = self._tpl_library_exists.format(library_name)
            else:
                status_text = self._tpl_not_exists.format(library_name)

        if self._library_manager.is_library_loaded(key):
            generate_button_label = self._lbl_regenerate_library
        else:
            generate_button_label = self._lbl_generate_library

        view_model = LibraryPanelViewModel(
            status_text=status_text,
            generate_button_label=generate_button_label,
            is_generating=is_generating,
            progress_value=progress,
        )
        self.call(self.on_view_changed, view_model)
