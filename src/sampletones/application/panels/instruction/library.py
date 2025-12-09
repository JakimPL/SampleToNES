from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.configs import InstructionsLibraryConfig
from sampletones.constants.enums import GeneratorClassName
from sampletones.exceptions import (
    IncompatibleLibraryDataVersionError,
    InvalidLibraryDataError,
    InvalidLibraryDataValuesError,
    InvalidMetadataError,
    WindowNotAvailableError,
)
from sampletones.instructions import InstructionUnion
from sampletones.library import InstructionLibraryFragment, InstructionLibraryKey
from sampletones.parallelization import TaskProgress, TaskStatus
from sampletones.parallelization.progress import ETAEstimator
from sampletones.tree import (
    GeneratorNode,
    GroupNode,
    InstructionNode,
    LibraryNode,
    NodeType,
    TreeNode,
)
from sampletones.typehints import Sender
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import (
    MSG_GLOBAL_INVALID_METADATA_ERROR,
    SUF_PANEL_LEFT,
    TAG_TAB_INSTRUCTIONS,
    TPL_GLOBAL_TIME_ESTIMATION,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from ...constants.instructions import (
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_REGENERATE_LIBRARY,
    LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_INSTRUCTION,
    LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
    LBL_INSTRUCTIONS_LIBRARY_AVAILABLE_LIBRARIES,
    LBL_INSTRUCTIONS_LIBRARY_LIBRARIES,
    MSG_INSTRUCTIONS_LIBRARY_FILE_LOAD_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_FILE_NOT_FOUND,
    MSG_INSTRUCTIONS_LIBRARY_GENERATING,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_CANCELLATION,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_SAVING,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_SUCCESS,
    MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_VALUES_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_LOAD_ERROR,
    MSG_INSTRUCTIONS_LIBRARY_LOADING,
    MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE,
    TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
    TAG_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
    TAG_GROUP_INSTRUCTIONS_LIBRARY_CONTROLS,
    TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE,
    TAG_PANEL_INSTRUCTIONS_LIBRARY,
    TAG_PROGRESS_INSTRUCTIONS_LIBRARY,
    TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
    TAG_TREE_INSTRUCTIONS_LIBRARY,
    TAG_WINDOW_INSTRUCTIONS_LIBRARY_TREE,
    TPL_INSTRUCTIONS_LIBRARY_GENERATION_PROGRESS,
    TPL_INSTRUCTIONS_LIBRARY_INCOMPATIBLE_VERSION_ERROR,
    TPL_INSTRUCTIONS_LIBRARY_LIBRARY_EXISTS,
    TPL_INSTRUCTIONS_LIBRARY_LIBRARY_LOADED,
    TPL_INSTRUCTIONS_LIBRARY_NOT_EXISTS,
    TTL_DIALOG_LIBRARY_GENERATION_STATUS,
)
from ...constants.main import TAG_PANEL_MAIN_CONVERTER
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree import GUITreePanel
from ...library.manager import InstructionsLibraryManager
from ...utils.dialogs import (
    show_error_dialog,
    show_file_not_found_dialog,
    show_info_dialog,
)
from ...utils.dpg import dpg_configure_item, dpg_set_value
from ...utils.thread import concurrent

OnInstructionSelectedCallback = Callable[
    [GeneratorClassName, InstructionUnion, InstructionLibraryFragment[Any], InstructionsLibraryConfig], None
]
OnApplyLibraryConfigCallback = Callable[[InstructionLibraryKey], None]
OnLibraryLoadedCallback = Callable[[InstructionLibraryKey], None]


class GUIInstructionsLibraryPanel(GUITreePanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
    ) -> None:
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager

        library_directory = config_manager.get_library_directory()
        self.library_manager = InstructionsLibraryManager(
            library_directory,
            on_generation_start=self._on_generation_start,
            on_progress=self._update_status,
            on_completed=self._on_generation_completed,
            on_error=self._on_generation_error,
            on_cancelled=self._on_generation_cancelled,
        )

        self.eta_estimator: Optional[ETAEstimator] = None

        self._on_instruction_selected: Optional[OnInstructionSelectedCallback] = None
        self._on_apply_library_config: Optional[OnApplyLibraryConfigCallback] = None
        self._on_library_loaded: Optional[OnLibraryLoadedCallback] = None

        super().__init__(
            self.library_manager.tree,
            tag=TAG_PANEL_INSTRUCTIONS_LIBRARY,
            parent=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
            tree_tag=TAG_TREE_INSTRUCTIONS_LIBRARY,
            application_config_manager=self.application_config_manager,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_library_status()
            self._create_library_controls()
            self._create_library_tree()

        self._refresh_libraries()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_INSTRUCTIONS_LIBRARY_LIBRARIES)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_library_status(self) -> None:
        dpg.add_separator()
        dpg.add_text("", tag=TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS)

    def _create_library_controls(self) -> None:
        with dpg.group(tag=TAG_GROUP_INSTRUCTIONS_LIBRARY_CONTROLS):
            dpg.add_progress_bar(
                tag=TAG_PROGRESS_INSTRUCTIONS_LIBRARY,
                show=False,
                width=-1,
                default_value=VAL_GLOBAL_DEFAULT_FLOAT,
            )
            GUIButton(
                tag=TAG_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
                label=LBL_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
                width=-1,
                callback=self._refresh_libraries,
            )
            GUIButton(
                tag=TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
                label=LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
                width=-1,
                callback=self.generate_library,
                font=Font.BOLD,
            )

    def _create_library_tree(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_WINDOW_INSTRUCTIONS_LIBRARY_TREE):
            with dpg.group(tag=TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE):
                with dpg.tree_node(
                    label=LBL_INSTRUCTIONS_LIBRARY_AVAILABLE_LIBRARIES,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def refresh(self) -> None:
        self._refresh_libraries()

    @concurrent
    def _rebuild_tree(self) -> None:
        self._set_tree_enabled(False)
        try:
            self.library_manager.rebuild_tree()
            self.build_tree()
        finally:
            self._set_tree_enabled(True)
            self.update_status()

    def is_loaded(self) -> bool:
        return self.library_manager.is_library_loaded(self.config_manager.key)

    def update_status(self) -> None:
        key = self.config_manager.key
        library_name = self.library_manager.get_display_name_from_key(key)

        if self.library_manager.is_library_loaded(key):
            dpg_set_value(
                TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
                TPL_INSTRUCTIONS_LIBRARY_LIBRARY_LOADED.format(library_name),
            )
            dpg_configure_item(
                TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
                label=LBL_BUTTON_INSTRUCTIONS_LIBRARY_REGENERATE_LIBRARY,
            )
        elif self.library_manager.library_exists_for_key(key):
            dpg_set_value(
                TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
                TPL_INSTRUCTIONS_LIBRARY_LIBRARY_EXISTS.format(library_name),
            )
            dpg_configure_item(
                TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
                label=LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
            )
        else:
            dpg_set_value(
                TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
                TPL_INSTRUCTIONS_LIBRARY_NOT_EXISTS.format(library_name),
            )
            dpg_configure_item(
                TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
                label=LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
            )

        is_generating = self.library_manager.is_generating()
        dpg_configure_item(TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY, enabled=not is_generating)
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE, enabled=not is_generating)

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_CONTROLS, enabled=enabled)

    def _refresh_libraries(self) -> None:
        self.library_manager.set_library_directory(self.config_manager.get_library_directory())
        self.library_manager.gather_available_libraries()
        self._sync_with_config_key()
        self._rebuild_tree()

    def _sync_with_config_key(self) -> None:
        config_key = self.config_manager.key
        matching_key = self.library_manager.sync_with_config_key(config_key)
        if matching_key:
            self._set_current_library(matching_key, load_if_needed=True, apply_config=False)

    def _set_current_library(
        self,
        library_key: InstructionLibraryKey,
        load_if_needed: bool = True,
        apply_config: bool = False,
    ) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(library_key):
            self._load_library(library_key)

        if apply_config and self._on_apply_library_config:
            self._on_apply_library_config(library_key)

        self.update_status()

    def _load_library(self, library_key: InstructionLibraryKey) -> None:
        self._set_tree_enabled(False)
        try:
            self.library_manager.load_library(library_key)
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Library file not found for key {library_key}")
            show_file_not_found_dialog(
                self.library_manager.get_path(library_key),
                MSG_INSTRUCTIONS_LIBRARY_FILE_NOT_FOUND,
            )
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error loading library file for key {library_key}")
            show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_FILE_LOAD_ERROR)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in library file for key {library_key}")
            show_error_dialog(exception, MSG_GLOBAL_INVALID_METADATA_ERROR)
        except InvalidLibraryDataValuesError as exception:
            logger.error_with_traceback(exception, f"Library data contains invalid values for key {library_key}")
            show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_VALUES_ERROR)
        except InvalidLibraryDataError as exception:
            logger.error_with_traceback(exception, f"Invalid library data file for {library_key}")
            show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_INVALID_DATA_ERROR)
        except IncompatibleLibraryDataVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible library data version for key {library_key}: "
                f"{exception.actual_version} != expected {exception.expected_version}",
            )
            show_error_dialog(
                exception,
                TPL_INSTRUCTIONS_LIBRARY_INCOMPATIBLE_VERSION_ERROR.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except Exception as exception:
            logger.error_with_traceback(exception, f"Error loading library for key {library_key}")
            show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_LOAD_ERROR)
        finally:
            self._set_tree_enabled(True)

    def load_library_file(self, filepath: Path) -> None:
        library_key = self.library_manager.create_key_from_filename(filepath.name)
        self._load_library_and_set_current(library_key)
        self.update_status()

    def _build_tree_node(
        self,
        node: TreeNode,
        parent: str,
        library_node: Optional[LibraryNode] = None,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        handler_registry_tag = self._get_handler_registry_tag(node_tag)
        if node.node_type == NodeType.PLACEHOLDER:
            if library_node is None:
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
            self._apply_node_theme(node_tag, node)
            FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)

        elif isinstance(node, InstructionNode):
            dpg.add_selectable(
                label=node.name,
                parent=parent,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
            self._apply_node_theme(node_tag, node)
            FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)

        elif isinstance(node, (LibraryNode, GeneratorNode, GroupNode)):
            if isinstance(node, LibraryNode):
                library_node = node

            is_current = isinstance(node, LibraryNode) and self._is_current_library_node(node)
            should_expand = is_current or self._should_expand_node(node)
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=parent,
                default_open=should_expand,
            ):
                FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)
                self._apply_node_theme(node_tag, node)
                for child in node.children:
                    self._build_tree_node(
                        child,
                        node_tag,
                        library_node=library_node,
                    )

            if isinstance(node, LibraryNode):
                self._add_item_handler_registry(
                    tag=handler_registry_tag,
                    parent=node_tag,
                    node=node,
                    item_click_callback=self._on_library_node_clicked,
                )

    def _on_library_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: LibraryNode,
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_library_context_menu(user_data)

        return None

    def _on_instruction_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: InstructionNode,
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_instruction_context_menu(user_data)

        return None

    def _show_library_context_menu(self, node: LibraryNode) -> None:
        if not isinstance(node, LibraryNode) or node.node_type != NodeType.LIBRARY:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            min_size=(0, 0),
            modal=False,
        ):
            self._add_context_menu_text(node)
            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
                callback=lambda: self._load_library_and_set_current(node.library_key),
            )

    def _show_instruction_context_menu(self, node: InstructionNode) -> None:
        if not isinstance(node, InstructionNode) or node.node_type != NodeType.INSTRUCTION:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            min_size=(0, 0),
            modal=False,
        ):
            self._add_context_menu_text(node)
            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_INSTRUCTION,
                callback=self._on_selectable_clicked,
                user_data=node,
            )

    def _is_current_library_node(self, node: TreeNode) -> bool:
        if not isinstance(node, LibraryNode):
            return False

        return node.library_key == self.library_manager.current_library_key

    def _load_library_and_set_current(self, library_key: InstructionLibraryKey) -> None:
        self._load_library(library_key)
        self._set_current_library(
            library_key,
            load_if_needed=False,
            apply_config=True,
        )
        self._rebuild_tree()
        if self._on_library_loaded:
            self._on_library_loaded(library_key)

    def _on_load_library_clicked(self, sender: Sender, app_data: bool, user_data: InstructionLibraryKey) -> None:
        library_key = user_data
        dpg.set_item_label(sender, MSG_INSTRUCTIONS_LIBRARY_LOADING)
        self._load_library_and_set_current(library_key)

    def _on_selectable_clicked(self, sender: Sender, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if not self._on_instruction_selected:
            return

        if not isinstance(user_data, InstructionNode):
            return

        self._set_tree_enabled(False)
        try:
            config = self.config_manager.get_config()
            self._on_instruction_selected(
                user_data.generator_class_name,
                user_data.instruction,
                user_data.fragment,
                config.library,
            )
        finally:
            self._set_tree_enabled(True)
            self.update_status()

    def generate_library(self) -> None:
        if self.library_manager.is_generating():
            return

        config = self.config_manager.get_config()
        window = self.config_manager.get_window()
        if not window:
            exception = WindowNotAvailableError(MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE)
            logger.info("No FFT window available for library generation")
            show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_WINDOW_NOT_AVAILABLE)
            return

        dpg_set_value(TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS, MSG_INSTRUCTIONS_LIBRARY_GENERATING)
        dpg_configure_item(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, show=True)
        dpg_configure_item(TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY, show=False)
        dpg_set_value(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, VAL_GLOBAL_DEFAULT_FLOAT)
        self.library_manager.generate_library(config, window)

    def _update_status(self, task_status: TaskStatus, task_progress: TaskProgress) -> None:
        if not dpg.does_item_exist(TAG_PROGRESS_INSTRUCTIONS_LIBRARY):
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

        dpg_set_value(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, task_progress.get_progress())
        eta_string = self.eta_estimator.update(creator.completed_instructions)
        percent_string = self.eta_estimator.get_percent_string()
        dpg_configure_item(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, overlay=percent_string)

        status_text = TPL_INSTRUCTIONS_LIBRARY_GENERATION_PROGRESS.format(
            creator.completed_instructions,
            creator.total_instructions,
        )
        if eta_string:
            status_text += TPL_GLOBAL_TIME_ESTIMATION.format(eta_string=eta_string)

        dpg_set_value(TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS, status_text)

    def _set_generation_completed(self) -> None:
        dpg_set_value(TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS, MSG_INSTRUCTIONS_LIBRARY_GENERATION_SAVING)
        dpg_set_value(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, VAL_GLOBAL_PROGRESS_COMPLETE)

    def _set_generation_failed(self) -> None:
        dpg_set_value(
            TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
            MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED,
        )

    def _set_generation_cancelled(self) -> None:
        dpg_set_value(TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS, "Library generation cancelled.")

    def _on_generation_start(self) -> None:
        assert self.library_manager.creator is not None, "Library manager creator is not initialized"
        self.eta_estimator = ETAEstimator(self.library_manager.creator.total_instructions)

    def _on_generation_completed(self) -> None:
        dpg_configure_item(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, overlay="100%")
        if not dpg.get_item_configuration(TAG_PANEL_MAIN_CONVERTER)["show"]:
            show_info_dialog(
                self.tag,
                MSG_INSTRUCTIONS_LIBRARY_GENERATION_SUCCESS,
                TTL_DIALOG_LIBRARY_GENERATION_STATUS,
            )
        self._finalize_generation()

    def _on_generation_error(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED)
        self._finalize_generation_error(exception)

    def _on_generation_cancelled(self) -> None:
        show_info_dialog(
            self.tag,
            MSG_INSTRUCTIONS_LIBRARY_GENERATION_CANCELLATION,
            TTL_DIALOG_LIBRARY_GENERATION_STATUS,
        )
        self._finalize_generation()

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
        dpg_configure_item(TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY, show=True)
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE, enabled=True)
        dpg_configure_item(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, show=False)

    def _finalize_generation_error(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED)
        self.library_manager.cleanup_creator()
        self._restore_generation_panel()

    def set_callbacks(
        self,
        on_instruction_selected: Optional[OnInstructionSelectedCallback] = None,
        on_apply_library_config: Optional[OnApplyLibraryConfigCallback] = None,
        on_library_loaded: Optional[OnLibraryLoadedCallback] = None,
    ) -> None:
        if on_instruction_selected is not None:
            self._on_instruction_selected = on_instruction_selected
        if on_apply_library_config is not None:
            self._on_apply_library_config = on_apply_library_config
        if on_library_loaded is not None:
            self._on_library_loaded = on_library_loaded
