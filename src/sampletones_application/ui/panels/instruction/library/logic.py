import threading
from pathlib import Path
from typing import Callable, Optional

from sampletones_application.config.manager import ConfigManager
from sampletones_application.constants.general import (
    MSG_GLOBAL_INVALID_METADATA_ERROR,
    TPL_GLOBAL_TIME_ESTIMATION,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from sampletones_application.constants.instructions import (
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_REGENERATE_LIBRARY,
    MSG_INSTRUCTIONS_LIBRARY_DESERIALIZATION_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_FILE_LOAD_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_FILE_NOT_FOUND,
    MSG_INSTRUCTIONS_LIBRARY_GENERATING,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_SAVING,
    MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_VALUES_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_LOAD_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE,
    TPL_INSTRUCTIONS_LIBRARY_GENERATION_PROGRESS,
    TPL_INSTRUCTIONS_LIBRARY_INCOMPATIBLE_VERSION_ERROR,
    TPL_INSTRUCTIONS_LIBRARY_LIBRARY_EXISTS,
    TPL_INSTRUCTIONS_LIBRARY_LIBRARY_LOADED,
    TPL_INSTRUCTIONS_LIBRARY_NOT_EXISTS,
)
from sampletones_application.logic.library.manager import InstructionsLibraryManager
from sampletones_application.ui.panels.instruction.library.viewmodel import LibraryPanelViewModel
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.generators import GENERATOR_CLASS_MAP, GENERATOR_TO_INSTRUCTION_MAP, LIBRARY_GENERATOR_CLASS_MAP
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import InstructionLibraryKey, get_display_name_from_key
from sampletones_core.library.utils import create_key_from_filename
from sampletones_core.parallelization import ETAEstimator, TaskProgress, TaskStatus
from sampletones_core.structures.tree import Tree
from sampletones_shared.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    WindowNotAvailableError,
)
from sampletones_shared.exceptions.validation import DeserializationError
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin

OnLoadInstructionCallback = Callable[[InstructionUnion], None]
OnApplyLibraryConfigCallback = Callable[[InstructionLibraryKey], None]


class LibraryLogic(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
    ) -> None:
        self._config_manager = config_manager
        self._library_manager = library_manager
        self._eta_estimator: Optional[ETAEstimator] = None
        self._status_lock = threading.Lock()

        self._status_text: str = ""
        self._progress_visible: bool = False
        self._progress_value: float = VAL_GLOBAL_DEFAULT_FLOAT
        self._progress_overlay: str = ""
        self._generate_button_visible: bool = True

        self._lock_function: Optional[Callable[[], None]] = None
        self._unlock_function: Optional[Callable[[], None]] = None
        self._is_locked_function: Optional[Callable[[], bool]] = None

        self.on_rebuild_tree_needed: Optional[Callable[[], None]] = None
        self.on_view_changed: Optional[Callable[[LibraryPanelViewModel], None]] = None
        self.on_instruction_loaded: Optional[OnLoadInstructionCallback] = None
        self.on_apply_library_config: Optional[OnApplyLibraryConfigCallback] = None
        self.on_generation_completed_dialog: Optional[Callable[[], None]] = None
        self.on_generation_error_dialog: Optional[Callable[[Exception], None]] = None
        self.on_generation_cancelled_dialog: Optional[Callable[[], None]] = None
        self.on_load_file_not_found: Optional[Callable[[Path, str], None]] = None
        self.on_load_error: Optional[Callable[[Exception, str], None]] = None

        self._library_manager.set_callbacks(
            on_generation_start=self._on_generation_start,
            on_generation_progress=self._on_generation_progress,
            on_generation_completed=self._on_generation_completed,
            on_generation_error=self._on_generation_error,
            on_generation_cancelled=self._on_generation_cancelled,
        )

    def configure_lock(
        self,
        lock_function: Callable[[], None],
        unlock_function: Callable[[], None],
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

    def update_status(self) -> None:
        self._emit_view()

    def load_current_library(self) -> None:
        library_key = self._library_manager.get_library_key()
        if library_key is None:
            logger.warning("No library key specified for loading")
            return

        self.load_library_and_set_current(library_key)

    def load_library_file(self, filepath: Path) -> None:
        if self._is_locked:
            logger.warning("Library is already loading; please wait until it finishes")
            return

        try:
            library_key = create_key_from_filename(filepath.name)
        except ValueError as exception:
            logger.error_with_traceback(exception, f"Invalid library file name format: {filepath.name}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_LOAD_ERROR)
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

    def generate_library(self) -> None:
        if self._library_manager.is_generating():
            return

        config = self._config_manager.config
        window = self._config_manager.window

        if not window:
            exception = WindowNotAvailableError(MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE)
            logger.info("No FFT window available for library generation")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE)
            return

        self._progress_visible = True
        self._generate_button_visible = False
        self._progress_value = VAL_GLOBAL_DEFAULT_FLOAT
        self._emit_view(status_text_override=MSG_INSTRUCTIONS_LIBRARY_GENERATING)
        self._library_manager.generate_library(config, window)

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
                MSG_INSTRUCTIONS_LIBRARY_FILE_NOT_FOUND,
            )
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error loading library file for key {library_key}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_FILE_LOAD_ERROR)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in library file for key {library_key}")
            self.call(self.on_load_error, exception, MSG_GLOBAL_INVALID_METADATA_ERROR)
        except InvalidLibraryDataValuesError as exception:
            logger.error_with_traceback(exception, f"Library data contains invalid values for key {library_key}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_VALUES_ERROR)
        except InvalidLibraryDataError as exception:
            logger.error_with_traceback(exception, f"Invalid library data file for {library_key}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_ERROR)
        except IncompatibleLibraryDataVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible library data version for key {library_key}: "
                f"{exception.actual_version} != expected {exception.expected_version}",
            )
            self.call(
                self.on_load_error,
                exception,
                TPL_INSTRUCTIONS_LIBRARY_INCOMPATIBLE_VERSION_ERROR.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(exception, f"Deserialization error loading library for key {library_key}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_DESERIALIZATION_ERROR)
        except Exception as exception:  # TODO: narrow down exception types
            logger.error_with_traceback(exception, f"Error loading library for key {library_key}")
            self.call(self.on_load_error, exception, MSG_INSTRUCTIONS_LIBRARY_LOAD_ERROR)
        finally:
            self._do_unlock()

    def _on_generation_start(self) -> None:
        self._do_lock()
        assert self._library_manager.creator is not None, "Library manager creator is not initialized"
        self._eta_estimator = ETAEstimator(self._library_manager.creator.total_instructions)

    def _on_generation_progress(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        with self._status_lock:
            match task_status:
                case TaskStatus.COMPLETED:
                    self._progress_value = VAL_GLOBAL_PROGRESS_COMPLETE
                    self._emit_view(status_text_override=MSG_INSTRUCTIONS_LIBRARY_GENERATION_SAVING)
                case TaskStatus.FAILED:
                    self._emit_view(status_text_override=MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED)
                case TaskStatus.CANCELLED:
                    self._emit_view(status_text_override="Library generation cancelled.")
                case TaskStatus.RUNNING:
                    self._update_progress_state(task_progress)

    def _update_progress_state(self, task_progress: TaskProgress) -> None:
        creator = self._library_manager.creator
        assert creator is not None, "Library manager creator is not initialized"
        assert self._eta_estimator is not None, "ETA Estimator is not initialized"

        self._progress_value = task_progress.get_progress()
        eta_string = self._eta_estimator.update(creator.completed_instructions)
        self._progress_overlay = self._eta_estimator.get_percent_string()

        status_text = TPL_INSTRUCTIONS_LIBRARY_GENERATION_PROGRESS.format(
            creator.completed_instructions,
            creator.total_instructions,
        )
        if eta_string:
            status_text += TPL_GLOBAL_TIME_ESTIMATION.format(eta_string=eta_string)

        self._emit_view(status_text_override=status_text)

    def _on_generation_completed(self) -> None:
        self._progress_overlay = "100%"
        self._emit_view()
        self.call(self.on_generation_completed_dialog)
        self._finalize_generation()

    def _on_generation_error(self, exception: Exception) -> None:
        self.call(self.on_generation_error_dialog, exception)
        self._finalize_generation_error(exception)

    def _on_generation_cancelled(self) -> None:
        self.call(self.on_generation_cancelled_dialog)
        self._finalize_generation()

    def _finalize_generation(self) -> None:
        try:
            self._progress_visible = False
            self._generate_button_visible = True
            self._set_current_library(self._config_manager.key, load_if_needed=True, apply_config=False)
            self.refresh_libraries()
            self._library_manager.cleanup_creator()
        finally:
            self._do_unlock()

    def _finalize_generation_error(self, exception: Exception) -> None:
        try:
            self.call(self.on_generation_error_dialog, exception)
            self._progress_visible = False
            self._generate_button_visible = True
            self._library_manager.cleanup_creator()
            self.update_status()
        finally:
            self._do_unlock()

    def _emit_view(self, status_text_override: Optional[str] = None) -> None:
        key = self._config_manager.key
        library_name = get_display_name_from_key(key)
        is_generating = self._library_manager.is_generating()

        if status_text_override is not None:
            self._status_text = status_text_override
        elif not is_generating:
            if self._library_manager.is_library_loaded(key):
                self._status_text = TPL_INSTRUCTIONS_LIBRARY_LIBRARY_LOADED.format(library_name)
            elif self._library_manager.library_exists_for_key(key):
                self._status_text = TPL_INSTRUCTIONS_LIBRARY_LIBRARY_EXISTS.format(library_name)
            else:
                self._status_text = TPL_INSTRUCTIONS_LIBRARY_NOT_EXISTS.format(library_name)

        if self._library_manager.is_library_loaded(key):
            generate_button_label = LBL_BUTTON_INSTRUCTIONS_LIBRARY_REGENERATE_LIBRARY
        else:
            generate_button_label = LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY

        viewmodel = LibraryPanelViewModel(
            status_text=self._status_text,
            generate_button_label=generate_button_label,
            generate_button_enabled=not is_generating,
            generate_button_visible=self._generate_button_visible,
            progress_visible=self._progress_visible,
            progress_value=self._progress_value,
            progress_overlay=self._progress_overlay,
        )
        self.call(self.on_view_changed, viewmodel)
