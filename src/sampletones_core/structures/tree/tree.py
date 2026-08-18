from typing import Callable, Optional, Tuple, Type, TypeVar

from anytree import PreOrderIter

from .node import TreeNode

TreeNodeT = TypeVar("TreeNodeT", bound=TreeNode)


class Tree:
    """The rows a view renders, held as one root the whole shape hangs from.

    The tree states which rows exist, what they are called and how they nest, and every view reading
    it shows that one shape. What a view narrows to is the view's own, so several views share a tree
    and each of them filters on its own.
    """

    def __init__(self, root: Optional[TreeNode] = None) -> None:
        self.root = root

    def set_root(self, root: Optional[TreeNode]) -> None:
        self.root = root

    def get_root(self) -> Optional[TreeNode]:
        return self.root

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
