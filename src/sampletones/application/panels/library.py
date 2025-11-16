from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from sampletones.configs import LibraryConfig
from sampletones.constants.enums import GeneratorClassName
from sampletones.exceptions import WindowNotAvailableError
from sampletones.exceptions.library import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataError,
)
from sampletones.instructions import Instruction
from sampletones.library import LibraryFragment, LibraryKey
from sampletones.parallelization import TaskProgress, TaskStatus
from sampletones.parallelization.progress import ETAEstimator
from sampletones.tree import (
    GeneratorNode,
    GroupNode,
    InstructionNode,
    LibraryNode,
    TreeNode,
)
from sampletones.typehints import Sender
from sampletones.utils.logger import logger

from ..config.manager import ConfigManager
from ..constants import (
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BUTTON_GENERATE_LIBRARY,
    LBL_BUTTON_REFRESH_LIBRARIES,
    LBL_BUTTON_REGENERATE_LIBRARY,
    LBL_LIBRARY_AVAILABLE_LIBRARIES,
    LBL_LIBRARY_LIBRARIES,
    MSG_GLOBAL_WINDOW_NOT_AVAILABLE,
    MSG_LIBRARY_FILE_ERROR,
    MSG_LIBRARY_FILE_NOT_FOUND,
    MSG_LIBRARY_GENERATING,
    MSG_LIBRARY_GENERATION_CANCELLATION,
    MSG_LIBRARY_GENERATION_FAILED,
    MSG_LIBRARY_GENERATION_SUCCESS,
    MSG_LIBRARY_INCOMPATIBLE_VERSION_ERROR,
    MSG_LIBRARY_INVALID_DATA_ERROR,
    MSG_LIBRARY_LOAD_ERROR,
    MSG_LIBRARY_LOADING,
    MSG_LIBRARY_NOT_LOADED,
    NOD_TYPE_LIBRARY,
    NOD_TYPE_LIBRARY_PLACEHOLDER,
    TAG_LIBRARY_BUTTON_GENERATE,
    TAG_LIBRARY_BUTTON_REFRESH,
    TAG_LIBRARY_CONTROLS_GROUP,
    TAG_LIBRARY_PANEL,
    TAG_LIBRARY_PANEL_GROUP,
    TAG_LIBRARY_PROGRESS,
    TAG_LIBRARY_STATUS,
    TAG_LIBRARY_TREE,
    TAG_LIBRARY_TREE_GROUP,
    TITLE_DIALOG_LIBRARY_GENERATION_STATUS,
    TPL_LIBRARY_EXISTS,
    TPL_LIBRARY_GENERATION_PROGRESS,
    TPL_LIBRARY_LOADED,
    TPL_LIBRARY_NOT_EXISTS,
    TPL_TIME_ESTIMATION,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from ..elements.button import GUIButton
from ..elements.tree import GUITreePanel
from ..library.manager import LibraryManager
from ..utils.dialogs import (
    show_error_dialog,
    show_file_not_found_dialog,
    show_info_dialog,
)
from ..utils.dpg import dpg_configure_item, dpg_set_value


class GUILibraryPanel(GUITreePanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        library_directory = config_manager.get_library_directory()
        self.library_manager = LibraryManager(
            library_directory,
            on_generation_start=self._on_generation_start,
            on_progress=self._update_status,
            on_completed=self._on_generation_completed,
            on_error=self._on_generation_error,
            on_cancelled=self._on_generation_cancelled,
        )

        self.eta_estimator: Optional[ETAEstimator] = None

        self._on_instruction_selected: Optional[
            Callable[[GeneratorClassName, Instruction, LibraryFragment, LibraryConfig], None]
        ] = None
        self._on_apply_library_config: Optional[Callable[[LibraryKey], None]] = None

        super().__init__(
            tree=self.library_manager.tree,
            tag=TAG_LIBRARY_PANEL,
            parent=TAG_LIBRARY_PANEL_GROUP,
            width=DIM_PANEL_LIBRARY_WIDTH,
            height=DIM_PANEL_LIBRARY_HEIGHT,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, width=self.width, height=self.height, parent=self.parent):
            dpg.add_text(LBL_LIBRARY_LIBRARIES)
            dpg.add_separator()
            dpg.add_text(MSG_LIBRARY_NOT_LOADED, tag=TAG_LIBRARY_STATUS)

            with dpg.group(tag=TAG_LIBRARY_CONTROLS_GROUP):
                GUIButton(
                    tag=TAG_LIBRARY_BUTTON_REFRESH,
                    label=LBL_BUTTON_REFRESH_LIBRARIES,
                    width=-1,
                    callback=self._refresh_libraries,
                )
                GUIButton(
                    tag=TAG_LIBRARY_BUTTON_GENERATE,
                    label=LBL_BUTTON_GENERATE_LIBRARY,
                    width=-1,
                    callback=self._generate_library,
                )
                dpg.add_progress_bar(
                    tag=TAG_LIBRARY_PROGRESS,
                    show=False,
                    width=-1,
                    default_value=VAL_GLOBAL_DEFAULT_FLOAT,
                )

            dpg.add_separator()
            self.create_search(self.tag)
            dpg.add_separator()
            with dpg.group(tag=TAG_LIBRARY_TREE_GROUP):
                with dpg.tree_node(label=LBL_LIBRARY_AVAILABLE_LIBRARIES, tag=TAG_LIBRARY_TREE, default_open=True):
                    pass

    def refresh(self) -> None:
        self.library_manager.set_library_directory(self.config_manager.get_library_directory())
        self._refresh_libraries()

    def _rebuild_tree(self) -> None:
        self.library_manager.rebuild_tree()
        self.build_tree(TAG_LIBRARY_TREE)
        self.update_status()

    def initialize_libraries(self) -> None:
        self._refresh_libraries()

    def is_loaded(self) -> bool:
        return self.library_manager.is_library_loaded(self.config_manager.key)

    def update_status(self) -> None:
        key = self.config_manager.key
        library_name = self.library_manager._get_display_name_from_key(key)

        if self.library_manager.is_library_loaded(key):
            dpg_set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_LOADED.format(library_name))
            dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, label=LBL_BUTTON_REGENERATE_LIBRARY)
        elif self.library_manager.library_exists_for_key(key):
            dpg_set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_EXISTS.format(library_name))
            dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, label=LBL_BUTTON_GENERATE_LIBRARY)
        else:
            dpg_set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_NOT_EXISTS.format(library_name))
            dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, label=LBL_BUTTON_GENERATE_LIBRARY)

        is_generating = self.library_manager.is_generating()
        dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=not is_generating)
        dpg_configure_item(TAG_LIBRARY_TREE_GROUP, enabled=not is_generating)

    def _refresh_libraries(self) -> None:
        dpg_configure_item(TAG_LIBRARY_TREE_GROUP, enabled=False)
        self.library_manager.gather_available_libraries()
        self._sync_with_config_key()
        self._rebuild_tree()
        dpg_configure_item(TAG_LIBRARY_TREE_GROUP, enabled=True)

    def _sync_with_config_key(self) -> None:
        config_key = self.config_manager.key
        matching_key = self.library_manager.sync_with_config_key(config_key)
        if matching_key:
            self._set_current_library(matching_key, load_if_needed=True, apply_config=False)

    def _set_current_library(
        self,
        library_key: LibraryKey,
        load_if_needed: bool = True,
        apply_config: bool = False,
    ) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(library_key):
            self._load_library(library_key)

        if apply_config and self._on_apply_library_config:
            self._on_apply_library_config(library_key)

        self.update_status()

    def _load_library(self, library_key: LibraryKey) -> None:
        try:
            self.library_manager.load_library(library_key)
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Library file not found for key {library_key}")
            show_file_not_found_dialog(
                self.library_manager.get_path(library_key),
                MSG_LIBRARY_FILE_NOT_FOUND,
            )
        except (IOError, IsADirectoryError, OSError, PermissionError) as exception:
            logger.error_with_traceback(exception, f"Error loading library file for key {library_key}")
            show_error_dialog(exception, MSG_LIBRARY_FILE_ERROR)
        except InvalidLibraryDataError as exception:
            logger.error_with_traceback(exception, f"Invalid library data file for {library_key}")
            show_error_dialog(exception, MSG_LIBRARY_INVALID_DATA_ERROR)
        except IncompatibleLibraryDataVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible library data version for key {library_key}: "
                f"{exception.actual_version} != expected {exception.expected_version}",
            )
            show_error_dialog(
                exception,
                MSG_LIBRARY_INCOMPATIBLE_VERSION_ERROR.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except Exception as exception:
            logger.error_with_traceback(exception, f"Error loading library for key {library_key}")
            show_error_dialog(exception, MSG_LIBRARY_LOAD_ERROR)

    def _build_tree_node(self, node: TreeNode, parent: str) -> None:
        node_tag = self._generate_node_tag(node)

        if node.node_type == NOD_TYPE_LIBRARY_PLACEHOLDER:
            library_node = self._find_parent_library(node)
            if not library_node:
                return

            library_key = library_node.library_key
            dpg.add_selectable(
                label=node.name,
                parent=parent,
                callback=self._on_load_library_clicked,
                user_data=library_key,
                tag=node_tag,
                default_value=False,
            )
        elif isinstance(node, InstructionNode):
            dpg.add_selectable(
                label=node.name,
                parent=parent,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
        elif isinstance(node, (LibraryNode, GeneratorNode, GroupNode)):
            is_current = isinstance(node, LibraryNode) and self._is_current_library_node(node)
            should_expand = is_current or self._should_expand_node(node)
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent, default_open=should_expand):
                for child in node.children:
                    self._build_tree_node(child, node_tag)

    def _is_current_library_node(self, node: TreeNode) -> bool:
        if not isinstance(node, LibraryNode):
            return False
        return node.library_key == self.library_manager.current_library_key

    def _find_parent_library(self, node: TreeNode) -> Optional[LibraryNode]:
        current = node.parent
        while current is not None:
            if isinstance(current, LibraryNode) and current.node_type == NOD_TYPE_LIBRARY:
                return current
            current = current.parent
        return None

    def _on_load_library_clicked(self, sender: Sender, app_data: bool, user_data: LibraryKey) -> None:
        library_key = user_data
        dpg.set_item_label(sender, MSG_LIBRARY_LOADING)
        dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=False)
        self._load_library(library_key)
        self._set_current_library(library_key, load_if_needed=False, apply_config=True)
        self._rebuild_tree()
        dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=True)

    def _on_selectable_clicked(self, sender: Sender, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if not self._on_instruction_selected:
            return

        if not isinstance(user_data, InstructionNode):
            return

        config = self.config_manager.get_config()
        self._on_instruction_selected(
            user_data.generator_class_name,
            user_data.instruction,
            user_data.fragment,
            config.library,
        )

        self.update_status()

    def _generate_library(self) -> None:
        if self.library_manager.is_generating():
            return

        config = self.config_manager.get_config()
        window = self.config_manager.get_window()
        if not window:
            exception = WindowNotAvailableError(MSG_GLOBAL_WINDOW_NOT_AVAILABLE)
            logger.info("No FFT window available for library generation")
            show_error_dialog(exception, MSG_GLOBAL_WINDOW_NOT_AVAILABLE)
            return

        dpg_configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=False)
        dpg_set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATING)
        dpg_configure_item(TAG_LIBRARY_PROGRESS, show=True)
        dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, show=False)
        dpg_set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_DEFAULT_FLOAT)
        self.library_manager.generate_library(config, window)

    def _update_status(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        if not dpg.does_item_exist(TAG_LIBRARY_PROGRESS):
            return

        match task_status:
            case TaskStatus.COMPLETED:
                self._set_generation_completed()
            case TaskStatus.FAILED:
                self._set_generation_failed()
            case TaskStatus.CANCELLED:
                self._set_generation_cancelled()
            case TaskStatus.RUNNING:
                self._update_progress(task_progress)

    def _set_generation_running(self, task_progress: TaskProgress) -> None:
        self._update_progress(task_progress)

    def _update_progress(self, task_progress: TaskProgress) -> None:
        creator = self.library_manager.creator
        assert creator is not None, "Library manager creator is not initialized"
        assert self.eta_estimator is not None, "ETA Estimator is not initialized"

        dpg_set_value(TAG_LIBRARY_PROGRESS, task_progress.get_progress())
        eta_string = self.eta_estimator.update(creator.completed_instructions)
        percent_string = self.eta_estimator.get_percent_string()
        dpg_configure_item(TAG_LIBRARY_PROGRESS, overlay=percent_string)

        status_text = TPL_LIBRARY_GENERATION_PROGRESS.format(creator.completed_instructions, creator.total_instructions)
        if eta_string:
            status_text += TPL_TIME_ESTIMATION.format(eta_string=eta_string)

        dpg_set_value(TAG_LIBRARY_STATUS, status_text)

    def _set_generation_completed(self) -> None:
        dpg_set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATION_SUCCESS)
        dpg_set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)

    def _set_generation_failed(self) -> None:
        dpg_set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATION_FAILED)

    def _set_generation_cancelled(self) -> None:
        dpg_set_value(TAG_LIBRARY_STATUS, "Library generation cancelled.")

    def _on_generation_start(self) -> None:
        assert self.library_manager.creator is not None, "Library manager creator is not initialized"
        self.eta_estimator = ETAEstimator(self.library_manager.creator.total_instructions)

    def _on_generation_completed(self) -> None:
        dpg_configure_item(TAG_LIBRARY_PROGRESS, overlay="100%")
        show_info_dialog(MSG_LIBRARY_GENERATION_SUCCESS, TITLE_DIALOG_LIBRARY_GENERATION_STATUS)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_generation())

    def _on_generation_error(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_LIBRARY_GENERATION_FAILED)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_generation_error(exception))

    def _on_generation_cancelled(self) -> None:
        show_info_dialog(MSG_LIBRARY_GENERATION_CANCELLATION, TITLE_DIALOG_LIBRARY_GENERATION_STATUS)
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: self._finalize_generation())

    def _finalize_generation(self) -> None:
        self._set_current_library(
            self.config_manager.key,
            load_if_needed=True,
            apply_config=False,
        )
        self._refresh_libraries()
        self.library_manager.cleanup_creator()
        self._restore_generation_panel()

    def _restore_generation_panel(self) -> None:
        dpg_configure_item(TAG_LIBRARY_BUTTON_GENERATE, show=True)
        dpg_configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=True)
        dpg_configure_item(TAG_LIBRARY_TREE_GROUP, enabled=True)
        dpg_configure_item(TAG_LIBRARY_PROGRESS, show=False)

    def _finalize_generation_error(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_LIBRARY_GENERATION_FAILED)
        self.library_manager.cleanup_creator()
        self._restore_generation_panel()

    def set_callbacks(
        self,
        on_instruction_selected: Optional[Callable] = None,
        on_apply_library_config: Optional[Callable] = None,
    ) -> None:
        if on_instruction_selected is not None:
            self._on_instruction_selected = on_instruction_selected
        if on_apply_library_config is not None:
            self._on_apply_library_config = on_apply_library_config
