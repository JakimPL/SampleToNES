import threading
from typing import Any, Callable, Optional, Tuple

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
    TPL_LIBRARY_NOT_EXISTS,
    VAL_GLOBAL_DEFAULT_FLOAT,
    VAL_GLOBAL_PROGRESS_COMPLETE,
)
from constants.general import LIBRARY_DIRECTORY
from library.data import LibraryFragment
from library.key import LibraryKey
from typehints.instructions import InstructionUnion


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

    def initialize_libraries(self) -> None:
        self._refresh_libraries()
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)

    def update_status(self) -> None:
        config = self.config_manager.get_config()
        key = self.config_manager.key

        if not config or not key:
            dpg.set_value(TAG_LIBRARY_STATUS, MSG_CONFIG_NOT_READY)
            dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=False)
            return

        library_name = self.library_manager._get_display_name_from_key(key)
        if self.library_manager.library_exists_for_key(key):
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_REGENERATE_LIBRARY)
        else:
            dpg.set_value(TAG_LIBRARY_STATUS, TPL_LIBRARY_NOT_EXISTS.format(library_name))
            dpg.set_item_label(TAG_LIBRARY_BUTTON_GENERATE, LBL_BUTTON_GENERATE_LIBRARY)

        dpg.configure_item(TAG_LIBRARY_BUTTON_GENERATE, enabled=not self.is_generating)

    def _refresh_libraries(self) -> None:
        self.library_manager.gather_available_libraries()
        self.build_tree_ui(TAG_LIBRARY_TREE)
        key = self.config_manager.key
        if key is not None:
            self._sync_with_config_key(key)

    def _sync_with_config_key(self, config_key: LibraryKey) -> None:
        matching_display_name = self.library_manager.sync_with_config_key(config_key)
        if matching_display_name:
            self._set_current_library(matching_display_name, load_if_needed=True, apply_config=False)

    def _set_current_library(self, display_name: str, load_if_needed: bool = True, apply_config: bool = False) -> None:
        if load_if_needed and not self.library_manager.is_library_loaded(display_name):
            if self.library_manager.load_library(display_name):
                self.library_manager.refresh_library_node(display_name)
                self.build_tree_ui(TAG_LIBRARY_TREE)

        if apply_config:
            library_key = self.library_manager.get_library_key_for_config_update(display_name)
            if library_key and self._on_apply_library_config:
                self._on_apply_library_config(library_key)

    def _build_tree_node_ui(self, node: TreeNode, parent_tag: str) -> None:
        node_tag = self._generate_node_tag(node)

        if node.node_type == NOD_TYPE_LIBRARY_PLACEHOLDER:
            display_name = node.display_name if isinstance(node, LibraryNode) else ""
            dpg.add_selectable(
                label=node.name,
                parent=parent_tag,
                callback=self._on_load_library_clicked,
                user_data=display_name,
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
            is_current = node.node_type == NOD_TYPE_LIBRARY and self._is_current_library(node.name)
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent_tag, default_open=is_current):
                for child in node.children:
                    self._build_tree_node_ui(child, node_tag)

    def _is_current_library(self, display_name: str) -> bool:
        if not self.config_manager.key:
            return False
        expected_display_name = self.library_manager._get_display_name_from_key(self.config_manager.key)
        return display_name == expected_display_name

    def _on_load_library_clicked(self, sender: int, app_data: bool, user_data: str) -> None:
        display_name = user_data
        dpg.set_item_label(sender, MSG_LIBRARY_LOADING)
        if self.library_manager.load_library(display_name):
            self.library_manager.refresh_library_node(display_name)
            self.build_tree_ui(TAG_LIBRARY_TREE)
            self._set_current_library(display_name, load_if_needed=False, apply_config=True)

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if (
            isinstance(user_data, InstructionNode)
            and user_data.node_type == NOD_TYPE_INSTRUCTION
            and user_data.instruction is not None
        ):
            if self._on_instruction_selected:
                library_config = self.config_manager.get_config()
                if library_config is not None:
                    library_config = library_config.library
                    self._on_instruction_selected(
                        user_data.generator_class_name,
                        user_data.instruction,
                        user_data.fragment,
                        library_config=library_config,
                    )

    def _generate_library(self) -> None:
        if self.is_generating:
            return

        config = self.config_manager.get_config()
        if not config:
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
