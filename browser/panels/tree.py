from typing import Callable, Optional, Union

import dearpygui.dearpygui as dpg

from browser.panels.panel import GUIPanel
from browser.tree.node import TreeNode
from browser.tree.tree import Tree
from constants.browser import (
    DIM_SEARCH_BUTTON_WIDTH,
    DIM_SEARCH_INPUT_WIDTH,
    LBL_BUTTON_CLEAR_SEARCH,
    LBL_INPUT_SEARCH,
    MSG_GLOBAL_NO_RESULTS_FOUND,
    VAL_GLOBAL_DEFAULT_SLOT,
)


class GUITreePanel(GUIPanel):
    def __init__(self, tag: str, parent_tag: str, width: int = -1, height: int = -1) -> None:
        self.tree = Tree()
        self._selected_node_tag: Optional[Union[str, int]] = None
        self._on_node_selected: Optional[Callable] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None
        super().__init__(tag, parent_tag, width, height)

    def build_tree_ui(self, tree_root_tag: str) -> None:
        self._clear_children(tree_root_tag)
        root = self.tree.get_root()
        if root is None:
            if self.tree.is_filtered():
                dpg.add_text(MSG_GLOBAL_NO_RESULTS_FOUND, parent=tree_root_tag)
            return

        for child in root.children:
            self._build_tree_node_ui(child, tree_root_tag)

    def create_search_ui(self, parent_tag: str) -> None:
        self._search_input_tag = f"{self.tag}_search_input"
        self._search_button_tag = f"{self.tag}_search_button"

        with dpg.group(horizontal=True, parent=parent_tag):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=LBL_INPUT_SEARCH,
                callback=self._on_search_changed,
                width=DIM_SEARCH_INPUT_WIDTH,
            )
            dpg.add_button(
                label=LBL_BUTTON_CLEAR_SEARCH,
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=DIM_SEARCH_BUTTON_WIDTH,
            )

    def _build_tree_node_ui(self, node: TreeNode, parent_tag: str) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _should_expand_node(self, node: TreeNode) -> bool:
        if not self.tree.is_filtered():
            return False

        for descendant in node.descendants:
            if self.tree.is_matching_node(descendant):
                return True

        return False

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
        if self._selected_node_tag is not None and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)
        self._selected_node_tag = None

    def _on_search_changed(self, sender: int, query: str) -> None:
        if query:
            self.apply_filter(query, self._default_search_predicate)
        else:
            self.clear_filter()
        self._rebuild_tree_ui()

    def _on_clear_search_clicked(self) -> None:
        if self._search_input_tag is not None:
            dpg.set_value(self._search_input_tag, "")
        self.clear_filter()
        self._rebuild_tree_ui()

    def _default_search_predicate(self, node: TreeNode, query: str) -> bool:
        return query.lower() in node.name.lower()

    def _rebuild_tree_ui(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

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
