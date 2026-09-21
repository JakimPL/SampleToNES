from functools import partial
from pathlib import Path
from typing import Callable, Optional, Tuple

from sampletones_application.categories.estimate import time_estimation
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction.library_manager import (
    InstructionsLibraryManager,
)
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.view_model.instruction.library import (
    LibraryPanelViewModel,
)
from sampletones_core.configs import InstructionsLibraryConfig
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.generators import (
    GENERATOR_CLASS_MAP,
    GENERATOR_TO_CLASS_NAME_MAP,
    GENERATOR_TO_INSTRUCTION_MAP,
)
from sampletones_core.instructions import InstructionUnion
from sampletones_core.library import (
    InstructionLibraryData,
    InstructionLibraryKey,
    LibraryState,
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
OnApplyLibraryConfigCallback = Callable[[InstructionLibraryKey, Optional[InstructionsLibraryConfig]], None]


class LibraryLogic(CallbackMixin):
    """The Instructions tab's library catalog, and the generation that writes a library into it.

    A generation reports from the creator's own threads, so each report is queued for the render
    loop and taken there, where the catalog and the tree lock stand.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        library_manager: InstructionsLibraryManager,
        *,
        language_manager: LanguageManager,
        is_operation_active: Callable[[], bool],
    ) -> None:
        self._language_manager = language_manager
        self._config_manager = config_manager
        self._library_manager = library_manager
        self._is_operation_active = is_operation_active
        self._eta_estimator: Optional[ETAEstimator] = None

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
        self.on_generation_canceled: Optional[VoidCallback] = None
        self.on_load_file_not_found: Optional[Callable[[Path, str], None]] = None
        self.on_library_outdated: Optional[Callable[[InstructionLibraryKey], None]] = None
        self.on_load_error: Optional[Callable[[Exception, str], None]] = None

        self._msg_window_not_available = language_manager["instructions.library.message.status_window_not_available"]
        self._msg_load_error = language_manager["instructions.library.message.status_load_error"]

        self._library_manager.set_callbacks(
            on_generation_start=partial(CallbackQueue.add, self._on_generation_start),
            on_generation_progress=partial(CallbackQueue.add, self._on_generation_progress),
            on_generation_completed=partial(CallbackQueue.add, self._on_generation_completed),
            on_generation_error=partial(CallbackQueue.add, self._on_generation_error),
            on_generation_canceled=partial(CallbackQueue.add, self._on_generation_canceled),
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
    def current_library_key(self) -> Optional[InstructionLibraryKey]:
        return self._library_manager.current_library_key

    def is_library_generating(self) -> bool:
        return self._library_manager.is_generating()

    def config_library_state(self) -> LibraryState:
        """Where the library the configuration names stands for this build."""
        return self._library_manager.library_state(self._config_manager.key)

    def get_path(self, key: InstructionLibraryKey) -> Path:
        return self._library_manager.get_path(key)

    def rebuild_tree(self) -> None:
        self._library_manager.rebuild_tree()

    def refresh_libraries(self, load_if_needed: bool = True) -> None:
        self._library_manager.set_library_directory(self._config_manager.get_library_directory())
        self._library_manager.gather_available_libraries()
        self._sync_with_config_key(load_if_needed=load_if_needed)
        self.call(self.on_rebuild_tree_needed)

    def follow_config(self) -> None:
        """Follows a configuration change, reading the catalog afresh where the change names another
        library directory and repainting the status otherwise.

        A generation writes into the catalog it was started in, so the catalog follows a change at
        once, whatever is running; the tree it lists is drawn once the generation lets its lock go.
        """
        if self._library_manager.library_directory != self._config_manager.get_library_directory():
            self.refresh_libraries(load_if_needed=False)
            return

        self.update_status()

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
            logger.error_with_traceback(
                exception,
                f"Invalid library file name format: {filepath.name}",
            )
            self.call(self.on_load_error, exception, self._msg_load_error)
            return

        self.load_library_and_set_current(library_key)

    def load_generator(self, generator_name: GeneratorName) -> None:
        if self._is_locked:
            return

        generator_class = GENERATOR_CLASS_MAP[GENERATOR_TO_CLASS_NAME_MAP[generator_name]]
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

    def prepare_library(self) -> None:
        """Generates the library a conversion under the configuration searches, unless the one
        standing there is a library this build reads.

        A missing library is generated, and one built by another version is rebuilt in its place.
        The configuration stays as the reader set it.
        """
        if self.config_library_state() is not LibraryState.CURRENT:
            self.generate_library()

    def rebuild_library(self, library_key: InstructionLibraryKey) -> None:
        """Rebuilds the library ``library_key`` names, which another version built, for the settings
        it was built for, the exclusive-operation gate permitting.

        Those settings become the configuration's before the generation starts, which writes the
        library in the place of the one it replaces.
        """
        if self._is_operation_active():
            logger.warning("A conversion or library generation is already in progress")
            return

        self.call(self.on_apply_library_config, library_key, self._library_manager.stored_config(library_key))
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

        self._do_lock()
        self._library_manager.generate_library(config, window)
        self._emit_view(self._language_manager["instructions.library.message.status_generating"])

    def cancel_generation(self) -> None:
        self._library_manager.cancel_generation()

    def _sync_with_config_key(self, load_if_needed: bool = True) -> None:
        """Takes up the library the configuration names where this build reads it, loading it
        where ``load_if_needed`` asks, and repaints the status either way."""
        config_key = self._config_manager.key
        matching_key = self._library_manager.sync_with_config_key(config_key)
        if matching_key is not None and load_if_needed and not self._library_manager.is_library_loaded(matching_key):
            self._load_library(matching_key)

        self.update_status()

    def load_library_and_set_current(self, library_key: InstructionLibraryKey) -> None:
        """Opens the library ``library_key`` names and makes the settings it was built for the
        configuration's.

        A library this build reads is loaded, and its settings are applied once it is. A library
        another version built is put to the reader through ``on_library_outdated``, and a missing
        one is reported.
        """
        self._open_library(library_key)

    def load_library_generator(self, library_key: InstructionLibraryKey, generator_name: GeneratorName) -> None:
        """Opens the library ``library_key`` names and shows the default instruction of
        ``generator_name`` from it, once the library is loaded."""
        if self._open_library(library_key):
            self.load_generator(generator_name)

    def _open_library(self, library_key: InstructionLibraryKey) -> bool:
        """Opens the library ``library_key`` names, as :meth:`load_library_and_set_current` states.

        Returns:
            bool: Whether the library is loaded.
        """
        if self._is_locked:
            return False

        match self._library_manager.library_state(library_key):
            case LibraryState.OUTDATED:
                self.call(self.on_library_outdated, library_key)
                return False
            case LibraryState.MISSING:
                self._report_missing(library_key)
                return False

        library_data = self._load_library(library_key)
        if library_data is not None:
            self.call(self.on_apply_library_config, library_key, library_data.config)

        self.update_status()
        return library_data is not None

    def _report_missing(self, library_key: InstructionLibraryKey) -> None:
        logger.warning(f"Library file not found for key {library_key}")
        self.call(
            self.on_load_file_not_found,
            self._library_manager.get_path(library_key),
            self._language_manager["instructions.library.message.status_file_not_found"],
        )

    def _load_library(self, library_key: InstructionLibraryKey) -> Optional[InstructionLibraryData]:
        """Loads the library ``library_key`` names into the catalog as its current one.

        Returns:
            Optional[InstructionLibraryData]: The library loaded, or ``None`` where the tree is
                locked or the load failed, which is reported.
        """
        if self._is_locked:
            return None

        self._do_lock()
        try:
            library_data = self._library_manager.load_library(library_key)
            logger.info(f"Library loaded: {library_key}")
            return library_data
        except FileNotFoundError as exception:
            logger.error_with_traceback(
                exception,
                f"Library file not found for key {library_key}",
            )
            self.call(
                self.on_load_file_not_found,
                self._library_manager.get_path(library_key),
                self._language_manager["instructions.library.message.status_file_not_found"],
            )
        except (IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(
                exception,
                f"Error loading library file for key {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["instructions.library.message.status_file_load_error"],
            )
        except InvalidMetadataError as exception:
            logger.error_with_traceback(
                exception,
                f"Invalid metadata in library file for key {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["global.dialog.message.invalid_metadata_error"],
            )
        except InvalidLibraryDataValuesError as exception:
            logger.error_with_traceback(
                exception,
                f"Library data contains invalid values for key {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["instructions.library.message.status_invalid_data_values"],
            )
        except InvalidLibraryDataError as exception:
            logger.error_with_traceback(
                exception,
                f"Invalid library data file for {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["instructions.library.message.status_invalid_data"],
            )
        except IncompatibleLibraryDataVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible library data version for key {library_key}: "
                f"{exception.actual_version} != expected {exception.expected_version}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["instructions.library.template.incompatible_version_template"].format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except DeserializationError as exception:
            logger.error_with_traceback(
                exception,
                f"Deserialization error loading library for key {library_key}",
            )
            self.call(
                self.on_load_error,
                exception,
                self._language_manager["instructions.library.message.status_deserialization_error"],
            )
        except LoadLibraryError as exception:
            logger.error_with_traceback(exception, f"Error loading library for key {library_key}")
            self.call(self.on_load_error, exception, self._msg_load_error)
        finally:
            self._do_unlock()

        return None

    def _on_generation_start(self) -> None:
        assert self._library_manager.creator is not None, "Library manager creator is not initialized"
        self._eta_estimator = ETAEstimator(self._library_manager.creator.total_instructions)
        self.call(self.on_generation_state_changed)

    def _on_generation_progress(
        self,
        task_status: TaskStatus,
        task_progress: TaskProgress,
    ) -> None:
        """Paints a report of the generation under way."""
        match task_status:
            case TaskStatus.COMPLETED:
                self._emit_view(self._language_manager["instructions.library.message.status_saving"], progress=1.0)
            case TaskStatus.FAILED:
                self._emit_view(self._language_manager["instructions.library.message.status_generation_failed"])
            case TaskStatus.CANCELED:
                self._emit_view(self._language_manager["instructions.library.message.status_generation_canceled"])
            case TaskStatus.RUNNING:
                self._update_progress_state(task_progress)

    def _update_progress_state(self, task_progress: TaskProgress) -> None:
        creator = self._library_manager.creator
        assert creator is not None, "Library manager creator is not initialized"
        assert self._eta_estimator is not None, "ETA Estimator is not initialized"

        eta_seconds = self._eta_estimator.update(creator.completed_instructions)
        status_text = self._language_manager["instructions.library.template.generation_progress_template"].format(
            creator.completed_instructions,
            creator.total_instructions,
        )
        self._emit_view(
            status_text + time_estimation(self._language_manager, eta_seconds),
            progress=task_progress.fraction,
        )

    def _on_generation_completed(self) -> None:
        """Closes the generation and reads the catalog again, which lists the library it wrote."""
        self.call(self.on_generation_completed)
        self._close_generation()
        self.refresh_libraries(load_if_needed=False)

    def _on_generation_error(self, exception: Exception) -> None:
        self.call(self.on_generation_error, exception)
        self._close_generation()
        self.update_status()

    def _on_generation_canceled(self) -> None:
        self.call(self.on_generation_canceled)
        self._close_generation()
        self.update_status()

    def _close_generation(self) -> None:
        """Lets the creator go along with the tree lock the generation took when it was asked for,
        which loading a library and rebuilding the tree both yield to."""
        self._library_manager.release_creator()
        self._do_unlock()
        self.call(self.on_generation_state_changed)

    def _emit_view(
        self,
        status_text: Optional[str] = None,
        *,
        progress: float = 0.0,
    ) -> None:
        """Builds and emits the panel view model from freshly computed values.

        ``status_text`` of ``None`` renders the idle status and the Generate label read from the
        catalog. A generation's emits pass their status and progress explicitly, and its controls
        replace the idle ones, Generate included.
        """
        key = self._config_manager.key
        is_generating = self._library_manager.is_generating()
        generate_button_label = self._language_manager["instructions.library.label.generate_library_button"]

        if status_text is None:
            status_template, generate_button_label = self._idle_texts(key)
            status_text = status_template.format(get_display_name_from_key(key))

        view_model = LibraryPanelViewModel(
            status_text=status_text,
            generate_button_label=generate_button_label,
            is_generating=is_generating,
            progress_value=progress,
        )
        self.call(self.on_view_changed, view_model)

    def _idle_texts(self, key: InstructionLibraryKey) -> Tuple[str, str]:
        """The status template and the Generate label for the library ``key`` names while no
        generation runs."""
        if self._library_manager.is_library_loaded(key):
            return (
                self._language_manager["instructions.library.template.library_loaded_template"],
                self._language_manager["instructions.library.label.regenerate_library_button"],
            )

        match self._library_manager.library_state(key):
            case LibraryState.CURRENT:
                return (
                    self._language_manager["instructions.library.template.library_exists_template"],
                    self._language_manager["instructions.library.label.generate_library_button"],
                )
            case LibraryState.OUTDATED:
                return (
                    self._language_manager["instructions.library.template.library_outdated_template"],
                    self._language_manager["instructions.library.label.rebuild_library_button"],
                )
            case LibraryState.MISSING:
                return (
                    self._language_manager["instructions.library.template.library_not_exists_template"],
                    self._language_manager["instructions.library.label.generate_library_button"],
                )
