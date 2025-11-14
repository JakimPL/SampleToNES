from typing import Callable, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones.tree import Tree, TreeNode
from sampletones.typehints import Sender

from ..constants import (
    DIM_SEARCH_BUTTON_WIDTH,
    DIM_SEARCH_INPUT_WIDTH,
    LBL_BUTTON_CLEAR_SEARCH,
    LBL_INPUT_SEARCH,
    MSG_GLOBAL_NO_RESULTS_FOUND,
    SUF_SEARCH_BUTTON,
    SUF_SEARCH_INPUT,
)
from ..utils.common import dpg_delete_children
from .button import GUIButton
from .panel import GUIPanel


class GUITreePanel(GUIPanel):
    def __init__(
        self,
        tree: Tree,
        tag: str,
        parent: str,
        width: int = -1,
        height: int = -1,
    ) -> None:
        self.tree = tree
        self._selected_node_tag: Optional[Union[str, int]] = None
        self._on_node_selected: Optional[Callable] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None
        super().__init__(tag, parent, width, height)

    def build_tree(self, tree_root_tag: str) -> None:
        self._clear_children(tree_root_tag)
        root = self.tree.get_root()
        if root is None:
            if self.tree.is_filtered():
                dpg.add_text(MSG_GLOBAL_NO_RESULTS_FOUND, parent=tree_root_tag)
            return

        for child in root.children:
            self._build_tree_node(child, tree_root_tag)

    def create_search(self, parent: str) -> None:
        self._search_input_tag = f"{self.tag}{SUF_SEARCH_INPUT}"
        self._search_button_tag = f"{self.tag}{SUF_SEARCH_BUTTON}"

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=LBL_INPUT_SEARCH,
                callback=self._on_search_changed,
                width=DIM_SEARCH_INPUT_WIDTH,
            )
            GUIButton(
                label=LBL_BUTTON_CLEAR_SEARCH,
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=DIM_SEARCH_BUTTON_WIDTH,
            )

    def _build_tree_node(self, node: TreeNode, parent: str) -> None:
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

    def set_tree_callbacks(self, on_node_selected: Optional[Callable] = None) -> None:
        self._on_node_selected = on_node_selected
