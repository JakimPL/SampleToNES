from typing import Any, Callable, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones.constants import paths
from sampletones.tree import FileSystemNode, NodeType, Tree, TreeNode
from sampletones.typehints import Sender

from ..config.application.manager import ApplicationConfigManager
from ..constants.general import (
    DIM_BUTTON_WIDTH_SEARCH,
    DIM_INPUT_WIDTH_SEARCH,
    LBL_BUTTON_TREE_CLEAR_SEARCH,
    LBL_TREE_SEARCH,
    MSG_TREE_NO_RESULTS_FOUND,
    SUF_BUTTON_SEARCH,
    SUF_TREE_SEARCH_INPUT,
)
from ..themes.nodes.favorite import FavoriteChildNodeTheme, FavoriteNodeTheme
from ..themes.nodes.file import (
    LibraryFileNodeTheme,
    NoContentFileNodeTheme,
    ReconstructionFileNodeTheme,
    WaveFileNodeTheme,
)
from ..themes.nodes.library import (
    LibraryGeneratorNodeTheme,
    LibraryGroupNodeTheme,
    LibraryInstructionNodeTheme,
    LibraryLibraryNodeTheme,
)
from ..themes.theme import Theme
from ..utils.dpg import dpg_delete_children, dpg_delete_item
from .button import GUIButton
from .panel import GUIPanel


class GUITreePanel(GUIPanel):
    def __init__(
        self,
        tree: Tree,
        tag: str,
        parent: str,
        application_config_manager: ApplicationConfigManager,
        width: int = -1,
        height: int = -1,
        search_label: str = LBL_TREE_SEARCH,
    ) -> None:
        self.tree = tree
        self.application_config_manager = application_config_manager

        self._selected_node_tag: Optional[Union[str, int]] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None

        self._on_node_selected: Optional[Callable[..., Any]] = None

        self.search_label = search_label

        super().__init__(
            tag=tag,
            parent=parent,
            width=width,
            height=height,
        )

    def build_tree(self, tree_root_tag: str) -> None:
        self._clear_children(tree_root_tag)
        root = self.tree.get_root()
        if root is None:
            if self.tree.is_filtered():
                dpg.add_text(MSG_TREE_NO_RESULTS_FOUND, parent=tree_root_tag)
            return

        for child in root.children:
            self._build_tree_node(child, tree_root_tag)

    def create_search(self, parent: str) -> None:
        self._search_input_tag = f"{self.tag}{SUF_TREE_SEARCH_INPUT}"
        self._search_button_tag = f"{self.tag}{SUF_BUTTON_SEARCH}"

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=self.search_label,
                callback=self._on_search_changed,
                width=DIM_INPUT_WIDTH_SEARCH,
            )
            GUIButton(
                label=LBL_BUTTON_TREE_CLEAR_SEARCH,
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=DIM_BUTTON_WIDTH_SEARCH,
            )

    def _build_tree_node(
        self,
        node: TreeNode,
        parent: str,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _has_relevant_content(self, node: TreeNode) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    def _should_expand_node(self, node: TreeNode) -> bool:
        if not self.tree.is_filtered():
            return False

        for descendant in node.descendants:
            if self.tree.is_matching_node(descendant):
                return True

        return False

    def _add_item_handler_registry(
        self,
        tag: str,
        parent: str,
        item_click_callback: Callable[[Sender, Tuple[int, int], Any], None],
        item_double_click_callback: Optional[Callable[[Sender, Tuple[int, int], Any], None]],
        node: TreeNode,
    ) -> None:
        dpg_delete_item(tag)
        with dpg.item_handler_registry(tag=tag):
            if item_click_callback is not None:
                dpg.add_item_clicked_handler(
                    callback=item_click_callback,
                    user_data=node,
                )
            if item_double_click_callback is not None:
                dpg.add_item_double_clicked_handler(
                    callback=item_double_click_callback,
                    user_data=node,
                )

        dpg.bind_item_handler_registry(parent, tag)

    def _generate_node_tag(self, node: TreeNode) -> str:
        path_parts = [ancestor.name for ancestor in node.path]
        tag = f"{self.tag}_node_{'_'.join(path_parts)}"
        return tag.replace(" ", "_")

    def _on_selectable_clicked(self, sender: Sender, app_data: bool, user_data: TreeNode) -> None:
        if self._selected_node_tag and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)

        self._selected_node_tag = sender
        dpg.set_value(sender, True)

        if self._on_node_selected:
            self._on_node_selected(user_data)

    def clear_selection(self) -> None:
        if self._selected_node_tag is not None and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)
        self._selected_node_tag = None

    def _on_search_changed(self, sender: Sender, query: str) -> None:
        if query:
            self.apply_filter(query, self._default_search_predicate)
        else:
            self.clear_filter()
        self._rebuild_tree()

    def _on_clear_search_clicked(self) -> None:
        if self._search_input_tag is not None:
            dpg.set_value(self._search_input_tag, "")
        self.clear_filter()
        self._rebuild_tree()

    def _default_search_predicate(self, node: TreeNode, query: str) -> bool:
        return query.lower() in node.name.lower()

    def _rebuild_tree(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def apply_filter(self, query: str, predicate: Callable[[TreeNode, str], bool]) -> None:
        self.tree.apply_filter(query, predicate)

    def clear_filter(self) -> None:
        self.tree.clear_filter()

    def _clear_children(self, tag: str) -> None:
        dpg_delete_children(tag)

    def _is_node_favorite(self, node: TreeNode) -> bool:
        if not isinstance(node, FileSystemNode):
            return False

        return node.filepath in self.application_config_manager.favorites

    def _has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        current_node = node.parent
        while current_node is not None:
            if not isinstance(current_node, FileSystemNode):
                break

            if self._is_node_favorite(current_node):
                return True

            current_node = current_node.parent

        return False

    def _toggle_favorite(self, node: FileSystemNode) -> None:
        if self.application_config_manager is None:
            return

        self.application_config_manager.toggle_favorite(node.filepath)

    def _apply_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
        has_favorite_ancestor: bool = False,
    ) -> None:
        if isinstance(node, FileSystemNode):
            match node.node_type:
                case NodeType.DIRECTORY:
                    return self._apply_directory_node_theme(
                        node_tag,
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                    )

                case NodeType.FILE:
                    return self._apply_file_node_theme(
                        node_tag,
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                    )

        return self._apply_other_node_theme(node_tag, node)

    def _apply_directory_node_theme(
        self,
        node_tag: str,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
    ) -> None:
        has_content = self._has_relevant_content(node)
        is_favorite = self._is_node_favorite(node)

        theme: Optional[Theme] = None
        if is_favorite:
            theme = FavoriteNodeTheme()
        elif not has_content:
            theme = NoContentFileNodeTheme()
        elif has_favorite_ancestor:
            theme = FavoriteChildNodeTheme()

        if theme is not None:
            theme.bind_to_item(node_tag)

    def _apply_file_node_theme(
        self,
        node_tag: str,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
    ) -> None:
        is_favorite = self._is_node_favorite(node)

        theme: Optional[Theme] = None
        if is_favorite:
            theme = FavoriteNodeTheme()
        else:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    theme = ReconstructionFileNodeTheme()
                case paths.EXT_FILE_LIBRARY:
                    theme = LibraryFileNodeTheme()
                case paths.EXT_FILE_WAVE:
                    theme = WaveFileNodeTheme()
                case _ if has_favorite_ancestor:
                    theme = FavoriteChildNodeTheme()

        if theme is not None:
            theme.bind_to_item(node_tag)

    def _apply_other_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
    ) -> None:
        theme: Optional[Theme] = None
        match node.node_type:
            case NodeType.LIBRARY:
                theme = LibraryLibraryNodeTheme()
            case NodeType.GENERATOR:
                theme = LibraryGeneratorNodeTheme()
            case NodeType.GROUP:
                theme = LibraryGroupNodeTheme()
            case NodeType.INSTRUCTION:
                theme = LibraryInstructionNodeTheme()

        if theme is not None:
            theme.bind_to_item(node_tag)

    def set_tree_callbacks(self, on_node_selected: Optional[Callable[..., Any]] = None) -> None:
        self._on_node_selected = on_node_selected
