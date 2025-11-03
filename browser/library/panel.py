import threading
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.config.manager import ConfigManager
from browser.library.manager import LibraryManager
from browser.panels.tree import GUITreePanel
from browser.tree.node import InstructionNode, LibraryNode, TreeNode
from configs.config import Config
from constants.browser import (
    DIM_DIALOG_ERROR_HEIGHT,
    DIM_DIALOG_ERROR_WIDTH,
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BUTTON_GENERATE_LIBRARY,
    LBL_BUTTON_OK,
    LBL_BUTTON_REFRESH_LIBRARIES,
    LBL_BUTTON_REGENERATE_LIBRARY,
    LBL_LIBRARY_AVAILABLE_LIBRARIES,
    LBL_LIBRARY_LIBRARIES,
    MSG_CONFIG_NOT_READY,
    MSG_GLOBAL_WINDOW_NOT_AVAILABLE,
    MSG_LIBRARY_ERROR_GENERATING,
    MSG_LIBRARY_GENERATED_SUCCESSFULLY,
    MSG_LIBRARY_GENERATING,
    MSG_LIBRARY_LOADING,
    MSG_LIBRARY_NOT_LOADED,
    NOD_TYPE_INSTRUCTION,
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
    TITLE_DIALOG_ERROR,
    TPL_LIBRARY_EXISTS,
    TPL_LIBRARY_LOADED,
    TPL_LIBRARY_NOT_EXISTS,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from constants.general import LIBRARY_DIRECTORY
from library.key import LibraryKey


class GUILibraryPanel(GUITreePanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        library_directory = (
            config_manager.config.general.library_directory if config_manager.config else LIBRARY_DIRECTORY
        )
        self.library_manager = LibraryManager(library_directory)
        self.is_generating = False
        self.generation_thread = None

        self._on_instruction_selected: Optional[Callable] = None
        self._on_apply_library_config: Optional[Callable] = None

        super().__init__(
            tag=TAG_LIBRARY_PANEL,
            parent_tag=TAG_LIBRARY_PANEL_GROUP,
            width=DIM_PANEL_LIBRARY_WIDTH,
            height=DIM_PANEL_LIBRARY_HEIGHT,
        )

        self.tree = self.library_manager.tree

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, width=self.width, height=self.height, parent=self.parent_tag):
            dpg.add_text(LBL_LIBRARY_LIBRARIES)
            dpg.add_separator()
            dpg.add_text(MSG_LIBRARY_NOT_LOADED, tag=TAG_LIBRARY_STATUS)

            with dpg.group(tag=TAG_LIBRARY_CONTROLS_GROUP):
                dpg.add_button(
                    label=LBL_BUTTON_GENERATE_LIBRARY, callback=self._generate_library, tag=TAG_LIBRARY_BUTTON_GENERATE
                )
                dpg.add_button(label=LBL_BUTTON_REFRESH_LIBRARIES, callback=self._refresh_libraries)
                dpg.add_progress_bar(tag=TAG_LIBRARY_PROGRESS, show=False)

            dpg.add_separator()
            with dpg.tree_node(label=LBL_LIBRARY_AVAILABLE_LIBRARIES, tag=TAG_LIBRARY_TREE, default_open=True):
                pass

        self.update_status()

    def initialize_libraries(self) -> None:
        self._refresh_libraries()
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)

        self.update_status()

    def update_status(self) -> None:
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if config is None or key is None:
            dpg.set_value(TAG_LIBRARY_STATUS, MSG_CONFIG_NOT_READY)
            dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=False)
            return

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

    def _refresh_libraries(self) -> None:
        self.library_manager.gather_available_libraries()
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)
        self.build_tree_ui(TAG_LIBRARY_TREE)
        self.update_status()

    def _sync_with_config_key(self, config_key: LibraryKey) -> None:
        matching_key = self.library_manager.sync_with_config_key(config_key)
        if matching_key:
            self._set_current_library(matching_key, load_if_needed=True, apply_config=False)

    def _set_current_library(
        self, library_key: LibraryKey, load_if_needed: bool = True, apply_config: bool = False
    ) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(library_key):
            self.library_manager.load_library(library_key)
            self.library_manager.refresh_library_node(library_key)

        if apply_config and self._on_apply_library_config:
            self._on_apply_library_config(library_key)

        self.update_status()

    def _build_tree_node_ui(self, node: TreeNode, parent_tag: str) -> None:
        node_tag = self._generate_node_tag(node)

        if node.node_type == NOD_TYPE_LIBRARY_PLACEHOLDER:
            library_node = self._find_parent_library(node)
            if not library_node:
                return

            library_key = library_node.library_key
            dpg.add_selectable(
                label=node.name,
                parent=parent_tag,
                callback=self._on_load_library_clicked,
                user_data=library_key,
                tag=node_tag,
                default_value=False,
            )
        elif node.node_type == NOD_TYPE_INSTRUCTION:
            dpg.add_selectable(
                label=node.name,
                parent=parent_tag,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
        elif node.is_leaf:
            dpg.add_selectable(
                label=node.name,
                parent=parent_tag,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
        else:
            is_current = node.node_type == NOD_TYPE_LIBRARY and self._is_current_library_node(node)
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent_tag, default_open=is_current):
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
        self.library_manager.load_library(library_key)
        self.library_manager.refresh_library_node(library_key)
        self.build_tree_ui(TAG_LIBRARY_TREE)
        self._set_current_library(library_key, load_if_needed=False, apply_config=True)

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if not self._on_instruction_selected:
            return

        if not isinstance(user_data, InstructionNode):
            return

        config = self.config_manager.get_config()
        if config is None:
            return

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
        if config is None:
            return

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

        except Exception as exception:
            self._show_error_dialog(str(exception))

        finally:
            self.is_generating = False
            dpg.configure_item(TAG_LIBRARY_CONTROLS_GROUP, enabled=True)
            dpg.configure_item(TAG_LIBRARY_PROGRESS, show=False)

    def set_callbacks(
        self,
        on_instruction_selected: Optional[Callable] = None,
        on_apply_library_config: Optional[Callable] = None,
    ) -> None:
        self._on_instruction_selected = on_instruction_selected
        self._on_apply_library_config = on_apply_library_config

    def _show_error_dialog(self, error_message: str) -> None:
        if dpg.does_item_exist(TAG_DIALOG_ERROR_LIBRARY_GENERATION):
            dpg.delete_item(TAG_DIALOG_ERROR_LIBRARY_GENERATION)

        with dpg.window(
            label=TITLE_DIALOG_ERROR,
            tag=TAG_DIALOG_ERROR_LIBRARY_GENERATION,
            modal=True,
            width=DIM_DIALOG_ERROR_WIDTH,
            height=DIM_DIALOG_ERROR_HEIGHT,
            no_resize=True,
            on_close=lambda: dpg.delete_item(TAG_DIALOG_ERROR_LIBRARY_GENERATION),
        ):
            dpg.add_text(MSG_LIBRARY_ERROR_GENERATING)
            dpg.add_separator()
            dpg.add_text(error_message, wrap=DIM_DIALOG_ERROR_WIDTH - 20)
            dpg.add_separator()
            dpg.add_button(
                label=LBL_BUTTON_OK,
                callback=lambda: dpg.delete_item(TAG_DIALOG_ERROR_LIBRARY_GENERATION),
                width=-1,
            )
