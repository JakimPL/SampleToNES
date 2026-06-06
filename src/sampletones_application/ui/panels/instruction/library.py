from pathlib import Path
from typing import Any, Dict, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import TreeElements
from sampletones_application.categories.elements.instructions import InstructionsLibraryElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.general import (
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_INSTRUCTIONS,
)
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_REFRESH_LIBRARIES,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_CONTROLS,
    TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
    TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
    TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS,
    TAG_INSTRUCTIONS_LIBRARY_TREE,
    TAG_INSTRUCTIONS_LIBRARY_WINDOW_TREE,
)
from sampletones_application.constants.main import TAG_MAIN_CONVERTER_PANEL
from sampletones_application.layout.behavior import (
    SchedulingBehavior,
    TreeBehavior,
)
from sampletones_application.logic.instruction.library import LibraryLogic
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.utils.dialogs import DialogsRenderer
from sampletones_application.utils.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.thread import concurrent
from sampletones_application.view_model.instruction.library import LibraryPanelViewModel
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.structures.tree import (
    GeneratorNode,
    LibraryNode,
    NodeType,
    TreeNode,
    TreeTraversal,
    traverse,
)
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import MessageCallback


class GUIInstructionsLibraryPanel(GUITreePanel):
    def __init__(
        self,
        library_logic: LibraryLogic,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        *,
        scheduling: SchedulingBehavior,
        tree_behavior: TreeBehavior,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        favorite_color: ColorRGBA,
        node_color: ColorRGBA,
    ) -> None:
        self.library_logic = library_logic
        self._dialogs = dialogs
        self._tree_behavior = tree_behavior

        self._lbl_generate = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.GENERATE_LIBRARY_BUTTON,
        ]
        self._lbl_refresh = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.REFRESH_LIBRARIES_BUTTON,
        ]
        self._lbl_libraries = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.LIBRARIES_TEXT,
        ]
        self._lbl_available_libraries = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.AVAILABLE_LIBRARIES_TEXT,
        ]
        self._lbl_ctx_load_generator = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.CONTEXT_LOAD_GENERATOR,
        ]
        self._lbl_ctx_load_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.CONTEXT_LOAD_LIBRARY,
        ]
        self._msg_generation_cancelled = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_CANCELLED,
        ]
        self._msg_generation_failed = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_FAILED,
        ]
        self._msg_generation_success = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_GENERATION_SUCCESS,
        ]
        self._msg_status_node_generator = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_NODE_GENERATOR,
        ]
        self._msg_status_node_library = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.MESSAGE,
            InstructionsLibraryElements.STATUS_NODE_LIBRARY,
        ]
        self._ttl_generation_status = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.TITLE,
            InstructionsLibraryElements.GENERATION_STATUS_DIALOG,
        ]

        self._node_handlers: Dict[NodeType, NodeHandler]

        super().__init__(
            self.library_logic.tree,
            tag=TAG_INSTRUCTIONS_LIBRARY_PANEL,
            parent=f"{TAG_GLOBAL_TAB_INSTRUCTIONS}{SUF_PANEL_LEFT}",
            tree_tag=TAG_INSTRUCTIONS_LIBRARY_TREE,
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
            shortcut_manager=shortcut_manager,
            scheduling=scheduling,
            search_label=language_manager[
                Page.GLOBAL,
                Panel.BROWSER,
                TextType.LABEL,
                TreeElements.SEARCH,
            ],
            language_manager=language_manager,
            favorite_color=favorite_color,
            node_color=node_color,
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
        section_text = dpg.add_text(self._lbl_libraries)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_library_status(self) -> None:
        dpg.add_separator()
        text = dpg.add_text("", tag=TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS)
        FontRegistry.bind_to_item(text, Font.REGULAR_SMALL)

    def _create_library_controls(self) -> None:
        with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_CONTROLS):
            dpg.add_progress_bar(
                tag=TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
                show=False,
                width=-1,
                default_value=0.0,
            )
            GUIButton(
                tag=TAG_INSTRUCTIONS_LIBRARY_BUTTON_REFRESH_LIBRARIES,
                label=self._lbl_refresh,
                width=-1,
                callback=self.refresh,
            )
            GUIButton(
                tag=TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
                label=self._lbl_generate,
                width=-1,
                callback=self.generate_library,
                font=Font.BOLD,
            )

    def _create_library_tree(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(
            tag=TAG_INSTRUCTIONS_LIBRARY_WINDOW_TREE,
            width=-1,
            height=-1,
        ):
            with dpg.group(tag=TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE):
                with dpg.tree_node(
                    label=self._lbl_available_libraries,
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
        dpg_set_value(TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS, viewmodel.status_text)
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
            label=viewmodel.generate_button_label,
            enabled=viewmodel.generate_button_enabled,
            show=viewmodel.generate_button_visible,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
            show=viewmodel.progress_visible,
            overlay=viewmodel.progress_overlay,
        )
        dpg_set_value(
            TAG_INSTRUCTIONS_LIBRARY_PROGRESS,
            viewmodel.progress_value,
        )

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_GROUP_TREE,
            enabled=enabled,
        )
        dpg_configure_item(
            TAG_INSTRUCTIONS_LIBRARY_GROUP_CONTROLS,
            enabled=enabled,
        )

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
            add_node_priority=self._tree_behavior.priority_add_node,
            add_handler_priority=self._tree_behavior.priority_add_handler,
        )

        state.parent = node_tag

    def _create_status_bar_message_function_for_instructions_node(
        self,
    ) -> MessageCallback:
        def message_function(*args: Any, user_data: Tuple[TreeNode, str], **kwargs: Any) -> str:
            node, _ = user_data
            match node.node_type:
                case NodeType.LIBRARY:
                    message = self._msg_status_node_library
                case NodeType.GENERATOR:
                    parent = node.parent
                    assert isinstance(node, GeneratorNode), "Node is not a GeneratorNode"
                    assert isinstance(parent, LibraryNode), "Generator node parent is not a LibraryNode"
                    message = self._msg_status_node_generator.format(
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
            label=self._lbl_ctx_load_library,
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
            label=self._lbl_ctx_load_generator,
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
        if not dpg.get_item_configuration(TAG_MAIN_CONVERTER_PANEL)["show"]:
            self._dialogs.show_info(
                self.tag,
                self._msg_generation_success,
                self._ttl_generation_status,
            )

    def _on_generation_error_dialog(self, exception: Exception) -> None:
        self._dialogs.show_error(exception, self._msg_generation_failed)

    def _on_generation_cancelled_dialog(self) -> None:
        self._dialogs.show_info(
            self.tag,
            self._msg_generation_cancelled,
            self._ttl_generation_status,
        )

    def _on_load_file_not_found(self, path: Path, message: str) -> None:
        self._dialogs.show_file_not_found(path, message)

    def _on_load_error(self, exception: Exception, message: str) -> None:
        self._dialogs.show_error(exception, message)
