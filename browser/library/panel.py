import threading
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.elements.tree import GUITreePanel
from browser.library.manager import LibraryManager
from browser.tree.node import (
    GeneratorNode,
    GroupNode,
    InstructionNode,
    LibraryNode,
    TreeNode,
)
from browser.utils import show_file_not_found_dialog, show_modal_dialog
from configs.config import Config
from constants.browser import (
    DIM_DIALOG_ERROR_WIDTH_WRAP,
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BUTTON_GENERATE_LIBRARY,
    LBL_BUTTON_REFRESH_LIBRARIES,
    LBL_BUTTON_REGENERATE_LIBRARY,
    LBL_LIBRARY_AVAILABLE_LIBRARIES,
    LBL_LIBRARY_LIBRARIES,
    MSG_GLOBAL_WINDOW_NOT_AVAILABLE,
    MSG_LIBRARY_ERROR_GENERATING,
    MSG_LIBRARY_FILE_NOT_FOUND,
    MSG_LIBRARY_GENERATED_SUCCESSFULLY,
    MSG_LIBRARY_GENERATING,
    MSG_LIBRARY_LOADING,
    MSG_LIBRARY_NOT_LOADED,
    NOD_TYPE_LIBRARY,
    NOD_TYPE_LIBRARY_PLACEHOLDER,
    TAG_DIALOG_ERROR_LIBRARY_GENERATION,
    TAG_LIBRARY_BUTTON_GENERATE,
    TAG_LIBRARY_CONTROLS_GROUP,
    TAG_LIBRARY_PANEL,
    TAG_LIBRARY_PANEL_GROUP,
    TAG_LIBRARY_PROGRESS,
    TAG_LIBRARY_STATUS,
    TAG_LIBRARY_TREE,
    TAG_LIBRARY_TREE_GROUP,
    TITLE_DIALOG_ERROR,
    TPL_LIBRARY_EXISTS,
    TPL_LIBRARY_LOADED,
    TPL_LIBRARY_NOT_EXISTS,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from library.key import LibraryKey
from utils.logger import logger


class GUILibraryPanel(GUITreePanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        library_directory = config_manager.get_library_directory()
        self.library_manager = LibraryManager(library_directory)

        self.is_generating = False
        self.generation_thread: Optional[threading.Thread] = None

        self._on_instruction_selected: Optional[Callable] = None
        self._on_apply_library_config: Optional[Callable] = None

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
                dpg.add_button(
                    label=LBL_BUTTON_REFRESH_LIBRARIES,
                    width=-1,
                    callback=self._refresh_libraries,
                )
                dpg.add_button(
                    label=LBL_BUTTON_GENERATE_LIBRARY,
                    width=-1,
                    callback=self._generate_library,
                    tag=TAG_LIBRARY_BUTTON_GENERATE,
                )
                dpg.add_progress_bar(
                    tag=TAG_LIBRARY_PROGRESS,
                    show=False,
                    width=-1,
                    default_value=VAL_GLOBAL_DEFAULT_FLOAT,
                )

            dpg.add_separator()
            self.create_search_ui(self.tag)
            dpg.add_separator()
            with dpg.group(tag=TAG_LIBRARY_TREE_GROUP):
                with dpg.tree_node(label=LBL_LIBRARY_AVAILABLE_LIBRARIES, tag=TAG_LIBRARY_TREE, default_open=True):
                    pass

        self.update_status()

    def refresh(self) -> None:
        self.library_manager.set_library_directory(self.config_manager.get_library_directory())
        self._refresh_libraries()

    def _rebuild_tree_ui(self) -> None:
        self.build_tree_ui(TAG_LIBRARY_TREE)

    def initialize_libraries(self) -> None:
        self._refresh_libraries()
        key = self.config_manager.key
        self._sync_with_config_key(key)
        self.update_status()

    def is_loaded(self) -> bool:
        key = self.config_manager.key
        return self.library_manager.is_library_loaded(key)

    def update_status(self) -> None:
        key = self.config_manager.key
        library_name = self.library_manager._get_display_name_from_key(key)

        if self.library_manager.is_library_loaded(key):
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_LOADED.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_REGENERATE_LIBRARY)
        elif self.library_manager.library_exists_for_key(key):
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_NOT_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_GENERATE_LIBRARY)

        dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=not self.is_generating)
        dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=not self.is_generating)

    def _refresh_libraries(self) -> None:
        dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=False)
        self.library_manager.gather_available_libraries()
        key = self.config_manager.key
        self._sync_with_config_key(key)
        self.build_tree_ui(TAG_LIBRARY_TREE)
        self.update_status()
        dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=True)

    def _sync_with_config_key(self, config_key: LibraryKey) -> None:
        matching_key = self.library_manager.sync_with_config_key(config_key)
        if matching_key:
            self._set_current_library(matching_key, load_if_needed=True, apply_config=False)

    def _set_current_library(
        self, library_key: LibraryKey, load_if_needed: bool = True, apply_config: bool = False
    ) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(library_key):
            self._load_library(library_key)

        if apply_config and self._on_apply_library_config:
            self._on_apply_library_config(library_key)

        self.update_status()

    def _load_library(self, library_key: LibraryKey) -> None:
        try:
            self.library_manager.load_library(library_key)
        except FileNotFoundError as error:
            logger.error_with_traceback(f"Failed to load library for key {library_key}", error)
            show_file_not_found_dialog(
                self.library_manager.get_path(library_key),
                MSG_LIBRARY_FILE_NOT_FOUND,
            )

    def _build_tree_node_ui(self, node: TreeNode, parent: str) -> None:
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
                    self._build_tree_node_ui(child, node_tag)

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

    def _on_load_library_clicked(self, sender: int, app_data: bool, user_data: LibraryKey) -> None:
        library_key = user_data
        dpg.set_item_label(sender, MSG_LIBRARY_LOADING)
        self._load_library(library_key)
        self.build_tree_ui(TAG_LIBRARY_TREE)
        self._set_current_library(library_key, load_if_needed=False, apply_config=True)

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
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
            library_config=config.library,
        )

    def _generate_library(self) -> None:
        if self.is_generating:
            return

        config = self.config_manager.get_config()
        self.is_generating = True
        dpg.configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=False)
        dpg.set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATING)
        dpg.configure_item(TAG_LIBRARY_PROGRESS, show=True)
        dpg.set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_DEFAULT_FLOAT)

        self.generation_thread = threading.Thread(target=self._generate_library_worker, args=(config,), daemon=True)
        self.generation_thread.start()

    def _generate_library_worker(self, config: Config) -> None:
        try:
            window = self.config_manager.get_window()
            if not window:
                raise ValueError(MSG_GLOBAL_WINDOW_NOT_AVAILABLE)

            self.library_manager.generate_library(config, window, overwrite=True)

            dpg.set_value(TAG_LIBRARY_STATUS, MSG_LIBRARY_GENERATED_SUCCESSFULLY)
            dpg.set_value(TAG_LIBRARY_PROGRESS, VAL_GLOBAL_PROGRESS_COMPLETE)
            self.update_status()

        except Exception as exception:  # TODO: specify exception type
            logger.error_with_traceback("Library generation failed", exception)
            self._show_error_dialog(str(exception))

        finally:
            self.is_generating = False
            dpg.configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=True)
            dpg.configure_item(TAG_LIBRARY_TREE_GROUP, enabled=True)
            dpg.configure_item(TAG_LIBRARY_PROGRESS, show=False)

    def set_callbacks(
        self,
        on_instruction_selected: Optional[Callable] = None,
        on_apply_library_config: Optional[Callable] = None,
    ) -> None:
        if on_instruction_selected is not None:
            self._on_instruction_selected = on_instruction_selected
        if on_apply_library_config is not None:
            self._on_apply_library_config = on_apply_library_config

    def _show_error_dialog(self, error_message: str) -> None:
        def content(parent: str) -> None:
            dpg.add_text(MSG_LIBRARY_ERROR_GENERATING, parent=parent)
            dpg.add_separator(parent=parent)
            dpg.add_text(error_message, wrap=DIM_DIALOG_ERROR_WIDTH_WRAP, parent=parent)

        show_modal_dialog(
            tag=TAG_DIALOG_ERROR_LIBRARY_GENERATION,
            title=TITLE_DIALOG_ERROR,
            content=content,
        )
