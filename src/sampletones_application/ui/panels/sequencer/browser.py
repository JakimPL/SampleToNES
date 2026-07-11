from typing import Any, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import TreeElements
from sampletones_application.categories.elements.sequencer import (
    SequencerBrowserElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior import TreeBehavior
from sampletones_application.tags.general import TAG_GLOBAL_THEME_SECONDARY_BUTTON
from sampletones_application.tags.sequencer import (
    TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
    TAG_SEQUENCER_BROWSER_GROUP_CONTROLS,
    TAG_SEQUENCER_BROWSER_GROUP_TREE,
    TAG_SEQUENCER_BROWSER_PANEL,
    TAG_SEQUENCER_BROWSER_TREE,
    TAG_SEQUENCER_BROWSER_WINDOW_TREE,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import context_menu
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    TreeTraversal,
    traverse,
)
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class GUISequencerBrowserPanel(GUITreePanel):
    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        shortcut_manager: ShortcutManager,
        *,
        tree_behavior: TreeBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
    ) -> None:
        self.on_refresh_tree: Optional[VoidCallback] = None

        self._tree_behavior = tree_behavior
        self._lbl_refresh = language_manager[
            Page.SEQUENCER,
            Panel.BROWSER,
            TextType.LABEL,
            SequencerBrowserElements.REFRESH_BUTTON,
        ]
        self._lbl_reconstructions = language_manager[
            Page.SEQUENCER,
            Panel.BROWSER,
            TextType.LABEL,
            SequencerBrowserElements.RECONSTRUCTIONS_TREE,
        ]

        self._node_handlers: Dict[NodeType, NodeHandler]

        super().__init__(
            tree=tree,
            tag=TAG_SEQUENCER_BROWSER_PANEL,
            tree_tag=TAG_SEQUENCER_BROWSER_TREE,
            tree_logic=tree_logic,
            shortcut_manager=shortcut_manager,
            search_label=language_manager[
                Page.GLOBAL,
                Panel.BROWSER,
                TextType.LABEL,
                TreeElements.SEARCH,
            ],
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
        )

    def create_panel(self, parent: str) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=parent,
            border=False,
        ):
            self._create_section_text()
            self._create_buttons()
            dpg.add_separator()
            self._create_tree_window()

        self._create_detail_tooltip(TAG_SEQUENCER_BROWSER_WINDOW_TREE)
        self.rebuild_tree()

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
        self._create_section_header(
            self._lbl_reconstructions,
            glyph=self._glyphs.headers.reconstruction,
        )

    def _create_buttons(self) -> None:
        with dpg.group(tag=TAG_SEQUENCER_BROWSER_GROUP_CONTROLS):
            GUIButton(
                tag=TAG_SEQUENCER_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
                label=self._lbl_refresh,
                width=-1,
                callback=self.rebuild_tree,
                theme=ThemeRegistry.get(TAG_GLOBAL_THEME_SECONDARY_BUTTON),
            )

    def _create_tree_window(self) -> None:
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_SEQUENCER_BROWSER_WINDOW_TREE):
            with dpg.group(tag=TAG_SEQUENCER_BROWSER_GROUP_TREE):
                with dpg.tree_node(
                    label=self._lbl_reconstructions,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def refresh(self) -> None:
        self.rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self.call(self.on_refresh_tree)
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

        is_favorite = self._logic.is_node_favorite(node)
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

    def set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_SEQUENCER_BROWSER_GROUP_TREE, enabled=enabled)
        dpg_configure_item(TAG_SEQUENCER_BROWSER_GROUP_CONTROLS, enabled=enabled)

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
            self._logic.request_autoplay(node)

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
            self._logic.cancel_autoplay()
            self.call(self.on_add_to_sequencer, node.filepath)

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_details(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)

    def _show_reconstruction_context_menu(self, node: FileSystemNode, node_tag: str) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_play_item(node)
            self._add_context_menu_sequencer_items(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_locate_audio_item(node)
            self._add_context_menu_favorite_item(node)
