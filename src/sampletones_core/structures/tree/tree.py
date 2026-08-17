from typing import Callable, Dict, Optional, Sequence, Tuple, Type, TypeVar

from anytree import PreOrderIter

from .node import TreeNode

TreeNodeT = TypeVar("TreeNodeT", bound=TreeNode)


class Tree:
    def __init__(self, root: Optional[TreeNode] = None) -> None:
        self.root = root
        self._filter_query: Optional[str] = None
        self._node_visibility: Dict[TreeNode, bool] = {}

    def set_root(self, root: Optional[TreeNode]) -> None:
        self.root = root
        self.clear_filter()

    def get_root(self) -> Optional[TreeNode]:
        return self.root

    def apply_filter(
        self,
        query: str,
        predicate: Callable[[TreeNode, str], bool],
    ) -> None:
        if not self.root:
            self._filter_query = query
            self._node_visibility = {}
            return

        if not query:
            self.clear_filter()
            return

        self._filter_query = query
        matching_nodes = {node for node in PreOrderIter(self.root) if predicate(node, query)}

        if not matching_nodes:
            self._node_visibility = {node: False for node in PreOrderIter(self.root)}
            return

        nodes_to_show = set(matching_nodes)
        for node in matching_nodes:
            current = node.parent
            while current is not None:
                nodes_to_show.add(current)
                current = current.parent

            for descendant in PreOrderIter(node):
                nodes_to_show.add(descendant)

        self._node_visibility = {node: node in nodes_to_show for node in PreOrderIter(self.root)}

    def clear_filter(self) -> None:
        self._filter_query = None
        self._node_visibility = {}

    def is_filtered(self) -> bool:
        return self._filter_query is not None

    def is_node_visible(self, node: TreeNode) -> bool:
        if not self.is_filtered():
            return True

        return self._node_visibility.get(node, False)

    def find_nodes(
        self,
        node_class: Type[TreeNodeT],
        predicate: Callable[[TreeNodeT], bool],
    ) -> Tuple[TreeNodeT, ...]:
        """Answers every node of ``node_class`` the predicate accepts, in reading order.

        One thing can stand in several places in a tree — a file listed by its configuration and
        again by the sample it came from — so a caller acting on a thing rather than on a row asks
        for all of its nodes at once. Naming the node class keeps the answer typed, so the caller
        reads the fields that class carries.
        """
        if self.root is None:
            return ()

        return tuple(
            node
            for node in PreOrderIter(self.root)
            if isinstance(
                node,
                node_class,
            )
            and predicate(node)
        )

    def collect_leaves(self) -> Sequence[TreeNode]:
        if not self.root:
            return []

        leaves = [node for node in PreOrderIter(self.root) if node.is_leaf]
        if self.is_filtered():
            return [leaf for leaf in leaves if self.is_node_visible(leaf)]

        return leaves
