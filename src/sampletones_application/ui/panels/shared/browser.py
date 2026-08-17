from abc import abstractmethod
from typing import Any, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.general import (
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FILE_WAVE,
)
from sampletones_application.ui.elements.context_menu import context_menu
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.browser import GUIFileBrowserPanel
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
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


class GUIReconstructionBrowserPanel(GUIFileBrowserPanel):
    """Shared skeleton of the reconstructions browser in the Sequencer and Reconstruction tabs.

    Reads the tree both tabs share into rows, colours the ones the browser invents, and routes node
    clicks to the subclass through :meth:`_open_reconstruction`. The subclass names its widgets and
    its refresh control, and adds the items its context menus offer.
    """

    _MONOSPACE_CONFIG_NODES: bool = True

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
    ) -> None:
        self._language_manager = language_manager
        self.on_refresh_tree: Optional[VoidCallback] = None

        super().__init__(
            tree=tree,
            tree_logic=tree_logic,
            scheduling=scheduling,
            search_label=language_manager["global.browser.label.search"],
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
            initial_collapsed=initial_collapsed,
        )

    @property
    def section_label(self) -> str:
        return self._language_manager["global.browser.label.browser"]

    @property
    def section_glyph(self) -> str:
        return self._glyphs.headers.reconstruction

    def _refresh_model(self) -> None:
        self.call(self.on_refresh_tree)

    def _setup_handlers(self) -> None:
        self._node_handlers = {
            NodeType.GROUP: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.GROUP),
                node_type=NodeType.GROUP,
            ),
            NodeType.SAMPLE: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.SAMPLE),
                node_type=NodeType.SAMPLE,
                status_bar_callback=self._create_status_bar_message_function_for_expandable_node(),
            ),
            **self._create_file_system_handlers(
                on_directory_clicked=self._on_directory_node_clicked,
                on_file_clicked=self._on_reconstruction_node_clicked,
                on_file_double_clicked=self._on_reconstruction_node_double_clicked,
                file_status_message=self._create_status_bar_message_function_for_reconstruction_node(),
            ),
        }

        super()._setup_handlers()

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
        match node.node_type:
            case NodeType.ROOT:
                return
            case NodeType.GROUP | NodeType.SAMPLE:
                self._append_spec(
                    node=node,
                    node_tag=node_tag,
                    parent=state.parent,
                    should_expand=self._should_expand_node(node),
                )
                state.parent = node_tag
                return

        if not isinstance(node, FileSystemNode):
            return

        self._mark_favorite_ancestry(node, state)
        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node)
            self._append_spec(
                node=node,
                node_tag=node_tag,
                parent=state.parent,
                should_expand=should_expand,
                has_favorite_ancestor=state.has_favorite_ancestor,
            )
        else:
            self._append_spec(
                node=node,
                node_tag=node_tag,
                parent=state.parent,
                leaf=True,
                has_favorite_ancestor=state.has_favorite_ancestor,
            )

        state.parent = node_tag

    def _resolve_other_theme_tag(self, node: TreeNode) -> str:
        """Selects the colour of a row the browser invents: a plain group, or a sample in wave colour.

        A sample row names the audio a set of reconstructions was made from, so it reads in the
        colour audio files carry elsewhere in the application.
        """
        match node.node_type:
            case NodeType.GROUP:
                return TAG_GLOBAL_THEME_DEFAULT
            case NodeType.SAMPLE:
                return TAG_GLOBAL_THEME_FILE_WAVE

        return super()._resolve_other_theme_tag(node)

    def _on_directory_node_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Right:
            self._show_directory_context_menu(node)

    def _on_reconstruction_node_clicked(
        self,
        _sender: Sender,
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
        _sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        """Opens the double-clicked reconstruction, dropping the preview the click before it queued.

        A single click queues an autoplay preview, and the second click of a double click means the
        reader wants the file itself, so the preview is dropped before the subclass opens it.
        """
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            self._logic.cancel_autoplay()
            self._open_reconstruction(node)

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_details(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_directory_context_menu_items(node)
            self._add_context_menu_favorite_item(node)

    def _show_reconstruction_context_menu(
        self,
        node: FileSystemNode,
        _node_tag: str,
    ) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_play_item(node)
            self._add_reconstruction_context_menu_items(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_locate_audio_item(node)
            self._add_context_menu_favorite_item(node)

    def _add_directory_context_menu_items(self, node: FileSystemNode) -> None:
        pass

    @abstractmethod
    def _add_reconstruction_context_menu_items(self, node: FileSystemNode) -> None: ...

    @abstractmethod
    def _open_reconstruction(self, node: FileSystemNode) -> None: ...
