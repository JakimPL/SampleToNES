from typing import Any, Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_core.audio import AudioDeviceManager
from sampletones_core.constants import paths
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode, TreeTraversal, traverse
from sampletones_shared.logger import logger
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, PathCallback

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import LBL_TREE_FILTER, SUF_PANEL_LEFT, TAG_TAB_MAIN, VAL_NODE_CHILDREN_SLOT
from ...constants.main import (
    LBL_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL,
    LBL_BUTTON_MAIN_EXPLORER_REFRESH,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_LIBRARY,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_RECONSTRUCTION,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_DIRECTORY,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_FILE,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_LIBRARY_DIRECTORY,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_OUTPUT_DIRECTORY,
    LBL_SECTION_MAIN_EXPLORER,
    MSG_MAIN_EXPLORER_CONVERTER_RUNNING,
    MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO,
    MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO_NO_AUTOPLAY,
    TAG_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL,
    TAG_BUTTON_MAIN_EXPLORER_REFRESH,
    TAG_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING,
    TAG_GROUP_MAIN_EXPLORER_CONTROLS,
    TAG_GROUP_MAIN_EXPLORER_TREE,
    TAG_PANEL_MAIN_EXPLORER,
    TAG_TREE_MAIN_EXPLORER,
    TAG_WINDOW_MAIN_EXPLORER_TREE,
    TTL_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING,
    VAL_PRIORITY_MAIN_EXPLORER_ADD_HANDLER,
    VAL_PRIORITY_MAIN_EXPLORER_ADD_NODE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree.handler import NodeHandler
from ...elements.tree.state import TreeNodeState
from ...elements.tree.tree import GUITreePanel
from ...explorer.manager import ExplorerManager
from ...utils.dialogs import show_info_dialog
from ...utils.dpg import dpg_configure_item, dpg_delete_children
from ...utils.shortcuts.manager import ShortcutManager
from ...utils.thread import concurrent


class GUIExplorerPanel(GUITreePanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self.explorer_manager = ExplorerManager(config_manager)
        self.audio_device_manager = audio_device_manager
        self.application_config_manager = application_config_manager
        self.shortcut_manager = shortcut_manager

        self._pending_autoplay_node: Optional[FileSystemNode] = None

        self._node_handlers: Dict[NodeType, NodeHandler]

        self.on_wave_file_clicked: Optional[PathCallback] = None
        self.on_directory_clicked: Optional[PathCallback] = None
        self.on_reconstruct_directory: Optional[PathCallback] = None
        self.on_reconstruct_file: Optional[PathCallback] = None
        self.on_load_reconstruction: Optional[PathCallback] = None
        self.on_load_library: Optional[PathCallback] = None
        self.on_set_as_output_directory: Optional[PathCallback] = None
        self.on_set_as_library_directory: Optional[PathCallback] = None
        self.is_converter_running: Optional[Callable[[], bool]] = None

        super().__init__(
            tree=self.explorer_manager.tree,
            tag=TAG_PANEL_MAIN_EXPLORER,
            parent=f"{TAG_TAB_MAIN}{SUF_PANEL_LEFT}",
            tree_tag=TAG_TREE_MAIN_EXPLORER,
            application_config_manager=application_config_manager,
            audio_device_manager=audio_device_manager,
            shortcut_manager=shortcut_manager,
            search_label=LBL_TREE_FILTER,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_buttons()
            self._create_tree_window()

        self._rebuild_tree()

    def _setup_handlers(self) -> None:
        self._node_handlers = {
            NodeType.DIRECTORY: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.DIRECTORY),
                node_type=NodeType.DIRECTORY,
                item_click_callback=self._on_directory_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_directory_node(),
            ),
            NodeType.FILE: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.FILE),
                node_type=NodeType.FILE,
                item_click_callback=self._on_file_node_clicked,
                item_double_click_callback=self._on_file_node_double_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_file_node(),
            ),
        }

        super()._setup_handlers()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_SECTION_MAIN_EXPLORER)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_buttons(self) -> None:
        dpg.add_separator()
        with dpg.group(tag=TAG_GROUP_MAIN_EXPLORER_CONTROLS):
            GUIButton(
                tag=TAG_BUTTON_MAIN_EXPLORER_REFRESH,
                label=LBL_BUTTON_MAIN_EXPLORER_REFRESH,
                parent=self.tag,
                width=-1,
                callback=self.refresh,
            )
            GUIButton(
                tag=TAG_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL,
                label=LBL_BUTTON_MAIN_EXPLORER_COLLAPSE_ALL,
                parent=self.tag,
                width=-1,
                callback=self.collapse_all,
            )

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_WINDOW_MAIN_EXPLORER_TREE):
            with dpg.group(tag=TAG_GROUP_MAIN_EXPLORER_TREE):
                with dpg.tree_node(
                    label=LBL_SECTION_MAIN_EXPLORER,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def collapse_all(self, sender: Sender, app_data: int, user_data: object) -> None:
        self.explorer_manager.collapse_all()
        children = dpg.get_item_children(self.tree_tag, VAL_NODE_CHILDREN_SLOT)
        assert children is not None, "Explorer tree has no children."
        for node_tag in children:
            dpg.set_value(node_tag, False)

    def refresh(self) -> None:
        self._rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self.explorer_manager.refresh_tree()
            self.build_tree()
        finally:
            self.unlock()

    def _rebuild_directory_node(self, node: FileSystemNode, node_tag: str) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self._rebuild_node_subtree(node, node_tag)
        finally:
            self.unlock()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_node_subtree(self, node: FileSystemNode, node_tag: str) -> None:
        if not dpg.does_item_exist(node_tag):
            return

        dpg_delete_children(node_tag)
        if self.explorer_manager.is_directory_expanded(node.filepath):
            for child in node.children:
                has_favorite_ancestor = self._is_node_favorite(node) or self._has_favorite_ancestor(child)
                self._build_tree_node(
                    child,
                    TreeNodeState(
                        parent=node_tag,
                        has_favorite_ancestor=has_favorite_ancestor,
                    ),
                )

    @traverse(TreeTraversal.BFS)
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, FileSystemNode):
            return

        is_favorite = self._is_node_favorite(node)
        state.has_favorite_ancestor |= is_favorite

        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node) or self.explorer_manager.is_directory_expanded(node.filepath)
            is_directory_expanded = self.explorer_manager.is_directory_expanded(node.filepath)
            self._queue_node(
                node,
                node_tag,
                state.parent,
                open_on_double_click=True,
                should_expand=should_expand,
                has_favorite_ancestor=state.has_favorite_ancestor,
                is_node_expanded=is_directory_expanded,
                add_node_priority=VAL_PRIORITY_MAIN_EXPLORER_ADD_NODE,
                add_handler_priority=VAL_PRIORITY_MAIN_EXPLORER_ADD_HANDLER,
            )
        else:
            self._queue_node(
                node,
                node_tag,
                state.parent,
                leaf=True,
                has_favorite_ancestor=state.has_favorite_ancestor,
                add_node_priority=VAL_PRIORITY_MAIN_EXPLORER_ADD_NODE,
                add_handler_priority=VAL_PRIORITY_MAIN_EXPLORER_ADD_HANDLER,
            )

        state.parent = node_tag

    def _create_status_bar_message_function_for_file_node(self) -> MessageCallback:
        reconstruction_message_function = self._create_status_bar_message_function_for_reconstruction_node()
        library_message_function = self._create_status_bar_message_function_for_library_node()
        audio_message_function = self._create_status_bar_message_function_for_audio_node()

        def message_function(*args: Any, user_data: Tuple[FileSystemNode, str], **kwargs: Any) -> str:
            node, _ = user_data
            suffix = node.filepath.suffix.lower()
            match suffix:
                case paths.EXT_FILE_RECONSTRUCTION:
                    return reconstruction_message_function(*args, user_data=user_data, **kwargs)
                case paths.EXT_FILE_LIBRARY:
                    return library_message_function(*args, user_data=user_data, **kwargs)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    return audio_message_function(*args, user_data=user_data, **kwargs)
                case _:
                    raise ValueError(f"Unsupported file type {suffix} for status bar message function.")

        return message_function

    def _on_file_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    return self._schedule_autoplay(node)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    self.call(self.on_wave_file_clicked, node.filepath)
                    return self._schedule_autoplay(node)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_file_context_menu(node)

        return None

    def _on_file_node_double_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    self._load_reconstruction(node)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    self._pending_autoplay_node = None
                    return self._reconstruct_file(node)
                case paths.EXT_FILE_LIBRARY:
                    return self._load_library(node)

        return None

    def _on_directory_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, node_tag = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            return self._directory_node_clicked(node, node_tag)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(node)

        return None

    def _create_status_bar_message_function_for_audio_node(self) -> MessageCallback:
        def message_function(*args: Any, **kwargs: Any) -> str:
            if self.application_config_manager.autoplay:
                return MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO

            return MSG_STATUS_NODE_MAIN_EXPLORER_AUDIO_NO_AUTOPLAY

        return self._create_status_bar_message_function(message_function)

    def _directory_node_clicked(self, node: FileSystemNode, node_tag: str) -> None:
        has_content = self.explorer_manager.has_relevant_content(node.filepath)
        if not has_content:
            return

        self._toggle_directory_expansion(node, node_tag)
        self.call(self.on_directory_clicked, node.filepath)

    def _load_reconstruction(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if filepath.exists():
            self.call(self.on_load_reconstruction, filepath)

    def _load_library(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if filepath.exists():
            self.call(self.on_load_library, filepath)

    def _has_relevant_content(self, node: TreeNode) -> bool:
        if isinstance(node, FileSystemNode):
            return self.explorer_manager.has_relevant_content(node.filepath)

        return True

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_MAIN_EXPLORER_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_MAIN_EXPLORER_CONTROLS, enabled=enabled)

    def _reconstruct_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_file, node.filepath)

    def _toggle_directory_expansion(self, node: FileSystemNode, node_tag: str) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        if not dpg.does_item_exist(node_tag):
            return

        is_directory_expanded = self.explorer_manager.is_directory_expanded(node.filepath)
        state = dpg.get_value(node_tag)
        if not is_directory_expanded:
            self.explorer_manager.expand_directory(node)
            self._rebuild_directory_node(node, node_tag)

        dpg.set_value(node_tag, not state)

    def _add_context_menu_file_actions(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        suffix = node.filepath.suffix.lower()
        match suffix:
            case paths.EXT_FILE_RECONSTRUCTION:
                dpg.add_menu_item(
                    label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_RECONSTRUCTION,
                    callback=lambda: self._load_reconstruction(node),
                )
            case paths.EXT_FILE_LIBRARY:
                dpg.add_menu_item(
                    label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_LOAD_LIBRARY,
                    callback=lambda: self._load_library(node),
                )
            case suffix if suffix in paths.EXT_FILES_AUDIO:
                dpg.add_menu_item(
                    label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_FILE,
                    callback=lambda: self._context_reconstruct_file(node),
                )

    def _show_file_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            modal=False,
        ):
            self._add_context_menu_text(node)
            self._add_context_menu_file_actions(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)

    def _add_context_menu_reconstruction_directory(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_DIRECTORY,
            callback=lambda: self._context_reconstruct_directory(node),
        )

    def _add_context_menu_reconstruction_file(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_RECONSTRUCT_FILE,
            callback=lambda: self._context_reconstruct_file(node),
        )

    def _add_context_menu_set_directory_items(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_OUTPUT_DIRECTORY,
            callback=lambda: self._context_set_as_output_directory(node),
        )

        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_MAIN_EXPLORER_SET_AS_LIBRARY_DIRECTORY,
            callback=lambda: self._context_set_as_library_directory(node),
        )

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            modal=False,
        ):
            self._add_context_menu_text(node)
            self._add_context_menu_reconstruction_directory(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)
            self._add_context_menu_set_directory_items(node)

    def _check_if_converter_running(self) -> bool:
        is_running = self.call(self.is_converter_running)
        if is_running:
            logger.warning("Conversion is already running. Wait or cancel the current operation.")
            show_info_dialog(
                tag=TAG_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING,
                message=MSG_MAIN_EXPLORER_CONVERTER_RUNNING,
                title=TTL_DIALOG_MAIN_EXPLORER_CONVERTER_RUNNING,
            )
            return True

        return False

    def _context_reconstruct_file(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_file, node.filepath)

    def _context_reconstruct_directory(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_directory, node.filepath)

    def _context_set_as_output_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_output_directory, node.filepath)

    def _context_set_as_library_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_library_directory, node.filepath)
