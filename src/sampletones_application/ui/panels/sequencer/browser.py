from typing import Any, Dict, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.config.application.manager import SessionManager
from sampletones_application.constants.general import SUF_PANEL_LEFT, TAG_TAB_GLOBAL_SEQUENCER
from sampletones_application.constants.sequencer import (
    TAG_BUTTON_SEQUENCER_BROWSER_REFRESH_RECONSTRUCTIONS,
    TAG_GROUP_SEQUENCER_BROWSER_CONTROLS,
    TAG_GROUP_SEQUENCER_BROWSER_TREE,
    TAG_PANEL_SEQUENCER_BROWSER,
    TAG_TREE_SEQUENCER_BROWSER,
    TAG_WINDOW_SEQUENCER_BROWSER_TREE,
)
from sampletones_application.layout.behavior import SchedulingBehavior, TreeBehavior
from sampletones_application.logic.sequencer.browser import SequencerBrowserLogic
from sampletones_application.text.elements.global_ import TreeElements
from sampletones_application.text.elements.sequencer import SequencerBrowserElements
from sampletones_application.text.hierarchy import Page, Panel, TextType
from sampletones_application.text.key import TextKey
from sampletones_application.text.manager import LanguageManager
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.utils.dpg import dpg_configure_item
from sampletones_application.utils.shortcuts.manager import ShortcutManager
from sampletones_application.utils.thread import concurrent
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode, TreeTraversal, traverse
from sampletones_shared.types.application import Sender


class GUISequencerBrowserPanel(GUITreePanel):
    def __init__(
        self,
        sequencer_browser_logic: SequencerBrowserLogic,
        session_manager: SessionManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        *,
        scheduling: SchedulingBehavior,
        tree_behavior: TreeBehavior,
        language_manager: LanguageManager,
    ) -> None:
        self.sequencer_browser_logic = sequencer_browser_logic
        self._tree_behavior = tree_behavior
        self._lbl_refresh = language_manager[
            TextKey(Page.SEQUENCER, Panel.BROWSER, TextType.LABEL, SequencerBrowserElements.REFRESH_BUTTON)
        ]
        self._lbl_reconstructions = language_manager[
            TextKey(Page.SEQUENCER, Panel.BROWSER, TextType.LABEL, SequencerBrowserElements.RECONSTRUCTIONS_TREE)
        ]

        self._node_handlers: Dict[NodeType, NodeHandler]

        super().__init__(
            tree=self.sequencer_browser_logic.tree,
            tag=TAG_PANEL_SEQUENCER_BROWSER,
            parent=f"{TAG_TAB_GLOBAL_SEQUENCER}{SUF_PANEL_LEFT}",
            tree_tag=TAG_TREE_SEQUENCER_BROWSER,
            session_manager=session_manager,
            audio_device_manager=audio_device_manager,
            shortcut_manager=shortcut_manager,
            scheduling=scheduling,
            search_label=language_manager[TextKey(Page.GLOBAL, Panel.BROWSER, TextType.LABEL, TreeElements.SEARCH)],
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
                item_click_callback=self._on_reconstruction_node_clicked,
                item_double_click_callback=self._on_reconstruction_node_double_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_reconstruction_node(),
            ),
        }

        super()._setup_handlers()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_reconstructions)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_buttons(self) -> None:
        dpg.add_separator()
        with dpg.group(tag=TAG_GROUP_SEQUENCER_BROWSER_CONTROLS):
            GUIButton(
                tag=TAG_BUTTON_SEQUENCER_BROWSER_REFRESH_RECONSTRUCTIONS,
                label=self._lbl_refresh,
                width=-1,
                callback=self._rebuild_tree,
            )

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_WINDOW_SEQUENCER_BROWSER_TREE):
            with dpg.group(tag=TAG_GROUP_SEQUENCER_BROWSER_TREE):
                with dpg.tree_node(
                    label=self._lbl_reconstructions,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def refresh(self) -> None:
        self._rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self.sequencer_browser_logic.refresh_tree()
            self.build_tree()
        finally:
            self.unlock()

    def _has_relevant_content(self, node: TreeNode) -> bool:
        if node.node_type == NodeType.FILE:
            return True

        return bool(node.children)

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

        is_favorite = self.logic.is_node_favorite(node)
        state.has_favorite_ancestor |= is_favorite
        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node)
            self._queue_node(
                node=node,
                node_tag=node_tag,
                parent=state.parent,
                should_expand=should_expand,
                has_favorite_ancestor=state.has_favorite_ancestor,
                add_node_priority=self._tree_behavior.priority_add_node,
                add_handler_priority=self._tree_behavior.priority_add_handler,
            )
        else:
            self._queue_node(
                node=node,
                node_tag=node_tag,
                parent=state.parent,
                leaf=True,
                has_favorite_ancestor=state.has_favorite_ancestor,
                add_node_priority=self._tree_behavior.priority_add_node,
                add_handler_priority=self._tree_behavior.priority_add_handler,
            )

        state.parent = node_tag

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_SEQUENCER_BROWSER_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_SEQUENCER_BROWSER_CONTROLS, enabled=enabled)

    def _on_directory_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(node)

        return None

    def _on_reconstruction_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, node_tag = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            self.logic.request_autoplay(node)

        if mouse_button == dpg.mvMouseButton_Right:
            self._show_reconstruction_context_menu(node, node_tag)

    def _on_reconstruction_node_double_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            self.logic.cancel_autoplay()
            self.call(self.on_add_to_sequencer, node.filepath)

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
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
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)

    def _show_reconstruction_context_menu(self, node: FileSystemNode, node_tag: str) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
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
            self._add_context_menu_sequencer_items(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)
