from typing import Callable, Optional, Sequence

from anytree import Node, PreOrderIter
from anytree.search import findall

from browser.tree.node import TreeNode


class Tree:
    def __init__(self, root: Optional[TreeNode] = None) -> None:
        self.root = root
        self._filter_query: Optional[str] = None
        self._filtered_root: Optional[TreeNode] = None

    def set_root(self, root: Optional[TreeNode]) -> None:
        self.root = root
        self.clear_filter()

    def get_root(self) -> Optional[TreeNode]:
        if self._filter_query is not None and self._filtered_root is not None:
            return self._filtered_root
        return self.root

    def apply_filter(self, query: str, predicate: Callable[[TreeNode, str], bool]) -> None:
        if not self.root:
            self._filtered_root = None
            self._filter_query = query
            return

        if not query:
            self.clear_filter()
            return

        self._filter_query = query
        matching_nodes = [node for node in PreOrderIter(self.root) if predicate(node, query)]

        if not matching_nodes:
            self._filtered_root = None
            return

        self._filtered_root = self._build_filtered_tree(matching_nodes)

    def _build_filtered_tree(self, matching_nodes: Sequence[TreeNode]) -> Optional[TreeNode]:
        if not matching_nodes:
            return None

        nodes_to_include = set(matching_nodes)
        for node in matching_nodes:
            current = node.parent
            while current is not None:
                nodes_to_include.add(current)
                current = current.parent

        node_map = {}
        for original_node in PreOrderIter(self.root):
            if original_node in nodes_to_include:
                parent_copy = node_map.get(original_node.parent) if original_node.parent else None
                node_copy = Node(original_node.name, parent=parent_copy)

                for attr_name in dir(original_node):
                    if not attr_name.startswith("_") and attr_name not in ["parent", "children", "name"]:
                        attr_value = getattr(original_node, attr_name, None)
                        if attr_value is not None and not callable(attr_value):
                            try:
                                setattr(node_copy, attr_name, attr_value)
                            except (AttributeError, TypeError):
                                pass

                node_map[original_node] = node_copy

        return node_map.get(self.root)

    def clear_filter(self) -> None:
        self._filter_query = None
        self._filtered_root = None

    def is_filtered(self) -> bool:
        return self._filter_query is not None

    def get_filter_query(self) -> Optional[str]:
        return self._filter_query

    def find_node(self, predicate: Callable[[TreeNode], bool]) -> Optional[TreeNode]:
        current_root = self.get_root()
        if not current_root:
            return None

        results = findall(current_root, filter_=predicate)
        return results[0] if results else None

    def collect_leaves(self) -> Sequence[TreeNode]:
        current_root = self.get_root()
        if not current_root:
            return []
        return [node for node in PreOrderIter(current_root) if node.is_leaf]

    def collect_all_nodes(self) -> Sequence[TreeNode]:
        current_root = self.get_root()
        if not current_root:
            return []
        return list(PreOrderIter(current_root))
