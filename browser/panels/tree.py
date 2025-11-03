from typing import Any, Callable, Optional, Union

import dearpygui.dearpygui as dpg
from anytree import PreOrderIter

from browser.panels.panel import GUIPanel
from browser.tree.node import TreeNode
from browser.tree.tree import Tree
from constants.browser import VAL_GLOBAL_DEFAULT_SLOT


class GUITreePanel(GUIPanel):
    def __init__(self, tag: str, parent_tag: str, width: int = -1, height: int = -1) -> None:
        self.tree = Tree()
        self._selected_node_tag: Optional[Union[str, int]] = None
        self._on_node_selected: Optional[Callable] = None
        super().__init__(tag, parent_tag, width, height)

    def build_tree_ui(self, tree_root_tag: str) -> None:
        self._clear_children(tree_root_tag)
        root = self.tree.get_root()
        if root is None:
            return

        for child in root.children:
            self._build_tree_node_ui(child, tree_root_tag)

    def _build_tree_node_ui(self, node: TreeNode, parent_tag: str) -> None:
        node_tag = self._generate_node_tag(node)

        if node.is_leaf:
            dpg.add_selectable(
                label=node.name,
                parent=parent_tag,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
        else:
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent_tag):
                for child in node.children:
                    self._build_tree_node_ui(child, node_tag)

    def _generate_node_tag(self, node: TreeNode) -> str:
        path_parts = [ancestor.name for ancestor in node.path]
        return f"{self.tag}_node_{'_'.join(path_parts)}"

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
        if self._selected_node_tag and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)

        self._selected_node_tag = sender
        dpg.set_value(sender, True)

        if self._on_node_selected:
            self._on_node_selected(user_data)

    def clear_selection(self) -> None:
        if self._selected_node_tag and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)
        self._selected_node_tag = None

    def apply_filter(self, query: str, predicate: Callable[[TreeNode, str], bool]) -> None:
        self.tree.apply_filter(query, predicate)

    def clear_filter(self) -> None:
        self.tree.clear_filter()

    def _clear_children(self, tag: str) -> None:
        children = dpg.get_item_children(tag, slot=VAL_GLOBAL_DEFAULT_SLOT) or []
        for child in children:
            dpg.delete_item(child)

    def set_tree_callbacks(self, on_node_selected: Optional[Callable] = None) -> None:
        self._on_node_selected = on_node_selected
