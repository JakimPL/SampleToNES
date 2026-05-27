from pathlib import Path
from typing import Any, Dict, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import ApplicationConfigManager
from sampletones_application.constants.general import (
    SUF_PANEL_LEFT,
    TAG_TAB_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
    LBL_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
    LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_GENERATOR,
    LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
    LBL_INSTRUCTIONS_LIBRARY_AVAILABLE_LIBRARIES,
    LBL_INSTRUCTIONS_LIBRARY_LIBRARIES,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_CANCELLATION,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED,
    MSG_INSTRUCTIONS_LIBRARY_GENERATION_SUCCESS,
    MSG_STATUS_NODE_INSTRUCTIONS_LIBRARY_GENERATOR,
    MSG_STATUS_NODE_INSTRUCTIONS_LIBRARY_LIBRARY,
    TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
    TAG_BUTTON_INSTRUCTIONS_LIBRARY_REFRESH_LIBRARIES,
    TAG_GROUP_INSTRUCTIONS_LIBRARY_CONTROLS,
    TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE,
    TAG_PANEL_INSTRUCTIONS_LIBRARY,
    TAG_PROGRESS_INSTRUCTIONS_LIBRARY,
    TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS,
    TAG_TREE_INSTRUCTIONS_LIBRARY,
    TAG_WINDOW_INSTRUCTIONS_LIBRARY_TREE,
    TTL_DIALOG_LIBRARY_GENERATION_STATUS,
    VAL_PRIORITY_INSTRUCTIONS_LIBRARY_ADD_HANDLER,
    VAL_PRIORITY_INSTRUCTIONS_LIBRARY_ADD_NODE,
)
from sampletones_application.constants.main import TAG_PANEL_MAIN_CONVERTER
from sampletones_application.logic.library.library import LibraryLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.utils.dialogs import show_error_dialog, show_file_not_found_dialog, show_info_dialog
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.thread import concurrent
from sampletones_application.view_model.library.library import LibraryPanelViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.structures.tree import GeneratorNode, LibraryNode, NodeType, TreeNode, TreeTraversal, traverse
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback


class GUIInstructionsLibraryPanel(GUITreePanel):
    def __init__(
        self,
        library_logic: LibraryLogic,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
    ) -> None:
        self.library_logic = library_logic

        self._node_handlers: Dict[NodeType, NodeHandler]

        super().__init__(
            self.library_logic.tree,
            tag=TAG_PANEL_INSTRUCTIONS_LIBRARY,
            parent=f"{TAG_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
            tree_tag=TAG_TREE_INSTRUCTIONS_LIBRARY,
            application_config_manager=application_config_manager,
            audio_device_manager=audio_device_manager,
            shortcut_manager=shortcut_manager,
        )

        self.library_logic.configure_lock(self.lock, self.unlock, lambda: self.locked)
        self.library_logic.on_rebuild_tree_needed = self._rebuild_tree
        self.library_logic.on_view_changed = self.update_view
        self.library_logic.on_generation_completed_dialog = self._on_generation_completed_dialog
        self.library_logic.on_generation_error_dialog = self._on_generation_error_dialog
        self.library_logic.on_generation_cancelled_dialog = self._on_generation_cancelled_dialog
        self.library_logic.on_load_file_not_found = self._on_load_file_not_found
        self.library_logic.on_load_error = self._on_load_error

    def _setup_handlers(self) -> None:
        self._node_handlers = {
            NodeType.LIBRARY: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.LIBRARY),
                node_type=NodeType.LIBRARY,
                item_click_callback=self._on_library_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_instructions_node(),
            ),
            NodeType.GENERATOR: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.GENERATOR),
                node_type=NodeType.GENERATOR,
                item_click_callback=self._on_generator_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_instructions_node(),
            ),
        }

        super()._setup_handlers()

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
            self._create_library_status()
            self._create_library_controls()
            self._create_library_tree()

        self.library_logic.refresh_libraries(load_if_needed=False)

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_INSTRUCTIONS_LIBRARY_LIBRARIES)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_library_status(self) -> None:
        dpg.add_separator()
        text = dpg.add_text("", tag=TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _create_library_controls(self) -> None:
        from sampletones_application.constants.general import VAL_GLOBAL_DEFAULT_FLOAT

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
                callback=self.refresh,
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
        with dpg.child_window(
            tag=TAG_WINDOW_INSTRUCTIONS_LIBRARY_TREE,
            width=-1,
            height=-1,
        ):
            with dpg.group(tag=TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE):
                with dpg.tree_node(
                    label=LBL_INSTRUCTIONS_LIBRARY_AVAILABLE_LIBRARIES,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def refresh(self) -> None:
        self.library_logic.refresh_libraries()

    def is_library_generating(self) -> bool:
        return self.library_logic.is_library_generating()

    def generate_library(self) -> None:
        self.library_logic.generate_library()

    def load_current_library(self) -> None:
        self.library_logic.load_current_library()

    def load_library_file(self, filepath: Path) -> None:
        self.library_logic.load_library_file(filepath)

    def update_view(self, viewmodel: LibraryPanelViewModel) -> None:
        dpg_set_value(TAG_TEXT_INSTRUCTIONS_LIBRARY_STATUS, viewmodel.status_text)
        dpg_configure_item(
            TAG_BUTTON_INSTRUCTIONS_LIBRARY_GENERATE_LIBRARY,
            label=viewmodel.generate_button_label,
            enabled=viewmodel.generate_button_enabled,
            show=viewmodel.generate_button_visible,
        )
        dpg_configure_item(
            TAG_PROGRESS_INSTRUCTIONS_LIBRARY,
            show=viewmodel.progress_visible,
            overlay=viewmodel.progress_overlay,
        )
        dpg_set_value(TAG_PROGRESS_INSTRUCTIONS_LIBRARY, viewmodel.progress_value)

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_INSTRUCTIONS_LIBRARY_CONTROLS, enabled=enabled)

    @concurrent(wait=False, method_bound=True)
    def _rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self.library_logic.rebuild_tree()
            self.build_tree()
        finally:
            self.unlock()
            self.library_logic.update_status()

    def _has_relevant_content(self, node: TreeNode) -> bool:
        return True

    @traverse(TreeTraversal.DFS)
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, (LibraryNode, GeneratorNode)):
            return

        if isinstance(node, LibraryNode):
            state.special_node = node

        is_current = isinstance(node, LibraryNode) and self._is_current_library_node(node)
        should_expand = is_current or self._should_expand_node(node)
        leaf = isinstance(node, GeneratorNode)
        self._queue_node(
            node,
            node_tag,
            state.parent,
            leaf=leaf,
            should_expand=should_expand,
            open_on_double_click=True,
            add_node_priority=VAL_PRIORITY_INSTRUCTIONS_LIBRARY_ADD_NODE,
            add_handler_priority=VAL_PRIORITY_INSTRUCTIONS_LIBRARY_ADD_HANDLER,
        )

        state.parent = node_tag

    def _create_status_bar_message_function_for_instructions_node(self) -> MessageCallback:
        def message_function(*args: Any, user_data: Tuple[TreeNode, str], **kwargs: Any) -> str:
            node, _ = user_data
            match node.node_type:
                case NodeType.LIBRARY:
                    message = MSG_STATUS_NODE_INSTRUCTIONS_LIBRARY_LIBRARY
                case NodeType.GENERATOR:
                    parent = node.parent
                    assert isinstance(node, GeneratorNode), "Node is not a GeneratorNode"
                    assert isinstance(parent, LibraryNode), "Generator node parent is not a LibraryNode"
                    message = MSG_STATUS_NODE_INSTRUCTIONS_LIBRARY_GENERATOR.format(
                        generator=node.generator_name,
                        library_key=parent.library_key.filename,
                    )
                case _:
                    raise ValueError(f"Unsupported node type '{node.node_type}' for status bar message function")

            return message

        return self._create_status_bar_message_function(message_function)

    def _on_generator_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[GeneratorNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            assert isinstance(node.parent, LibraryNode), "Generator node parent is not a LibraryNode"
            self.library_logic.load_library_and_set_current(node.parent.library_key)
            self.library_logic.load_generator(node.generator_name)

        if mouse_button == dpg.mvMouseButton_Right:
            self._show_generator_context_menu(node)

    def _on_library_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[LibraryNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, tag = user_data
        node_open = dpg.get_value(tag)
        if mouse_button == dpg.mvMouseButton_Left:
            dpg.set_value(tag, not node_open)
            if not node_open:
                self.library_logic.load_library_and_set_current(node.library_key)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_library_context_menu(node)

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
            self._add_context_menu_path_items(self.library_logic.get_path(node.library_key))
            self._add_context_menu_library_node(node)

    def _add_context_menu_library_node(self, node: LibraryNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
            callback=lambda: self.library_logic.load_library_and_set_current(node.library_key),
        )

    def _show_generator_context_menu(self, node: GeneratorNode) -> None:
        if not isinstance(node, GeneratorNode) or node.node_type != NodeType.GENERATOR:
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
            self._add_context_menu_generator_node(node)

    def _add_context_menu_generator_node(self, node: GeneratorNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=LBL_CONTEXT_ITEM_INSTRUCTIONS_LIBRARY_LOAD_GENERATOR,
            callback=self._on_load_generator,
            user_data=node,
        )

    def _is_current_library_node(self, node: TreeNode) -> bool:
        if not isinstance(node, LibraryNode):
            return False

        return node.library_key == self.library_logic.current_library_key

    def _on_load_generator(self, sender: Sender, app_data: bool, user_data: GeneratorNode) -> None:
        assert user_data.parent is not None, "Generator node parent is undefined"
        self.library_logic.load_library_and_set_current(user_data.parent.library_key)
        self.library_logic.load_generator(user_data.generator_name)

    def _on_generation_completed_dialog(self) -> None:
        if not dpg.get_item_configuration(TAG_PANEL_MAIN_CONVERTER)["show"]:
            show_info_dialog(
                self.tag,
                MSG_INSTRUCTIONS_LIBRARY_GENERATION_SUCCESS,
                TTL_DIALOG_LIBRARY_GENERATION_STATUS,
            )

    def _on_generation_error_dialog(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_INSTRUCTIONS_LIBRARY_GENERATION_FAILED)

    def _on_generation_cancelled_dialog(self) -> None:
        show_info_dialog(
            self.tag,
            MSG_INSTRUCTIONS_LIBRARY_GENERATION_CANCELLATION,
            TTL_DIALOG_LIBRARY_GENERATION_STATUS,
        )

    def _on_load_file_not_found(self, path: Path, message: str) -> None:
        show_file_not_found_dialog(path, message)

    def _on_load_error(self, exception: Exception, message: str) -> None:
        show_error_dialog(exception, message)
