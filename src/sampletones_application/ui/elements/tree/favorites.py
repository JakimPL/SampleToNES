from dataclasses import dataclass
from typing import Callable, List, Sequence, Set, Tuple

from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    TreeVisibility,
    resolve_visibility,
)


@dataclass(frozen=True)
class StarredRows:
    """The rows the favorites mode reads off a tree: the rows it draws, and the way down it opens.

    Attributes:
        tree: The model the rows are read from.
        logic: What answers which paths carry a star and which stars the mode follows.
        node_tag: The tag a row is drawn under.
    """

    tree: Tree
    logic: TreeLogicProtocol
    node_tag: Callable[[TreeNode], str]

    def resolve(self, *, follow_stars: bool) -> Tuple[TreeVisibility, Set[str]]:
        """The rows the favorites mode keeps, and the rows it opens the way down through.

        The two answer different questions — which rows the browser draws, and which of them stand
        open — so each is read out of one walk of the model: the rows a star reaches state what is
        drawn, and the rows above the anchors among them state the way down. A corpus of any size
        therefore resolves into a walk and a pair of sets.

        Args:
            follow_stars: Whether this pass is the one the reader started by switching the mode on,
                which is the pass that opens the way down to the stars.
        """
        reached = self.tree.find_nodes(TreeNode, self._is_starred)
        followed = self._followed_anchors(reached) if follow_stars else []
        return resolve_visibility(reached), self.way_down_to(followed)

    def way_down_to(self, rows: Sequence[TreeNode]) -> Set[str]:
        """The tags of the rows standing above these rows, which is a way down to them.

        A row given here is one the browser is pointed at, so a way down opens the rows above it while
        its own row stands as the reader left it. The container both branches hang from is a row on no
        screen, and stays out of the answer.
        """
        root = self.tree.get_root()
        return {self.node_tag(ancestor) for row in rows for ancestor in row.ancestors if ancestor is not root}

    def _followed_anchors(self, reached: Sequence[TreeNode]) -> List[TreeNode]:
        """The anchors whose star the reader asked the browser to open the way down to.

        Which stars are followed is a preference stated per kind and read once per pass: a starred
        reconstruction answers for itself, and a starred folder answers for itself together with the
        rows it brings in where no row stands for the folder.
        """
        reconstructions = self.logic.auto_expand_favorite_reconstructions
        directories = self.logic.auto_expand_favorite_directories
        return [
            node
            for node in reached
            if self._is_anchored(node) and (reconstructions if self._is_starred_reconstruction(node) else directories)
        ]

    def _is_starred_reconstruction(self, node: TreeNode) -> bool:
        """Whether the star the mode reaches this row through sits on a reconstruction.

        A row the reader starred answers by its own kind. A row a starred folder brings in answers by
        that folder, a folder being the only thing that holds another row.
        """
        return node.node_type == NodeType.FILE and self.logic.is_node_favorite(node)

    def _is_starred(self, node: TreeNode) -> bool:
        """Whether the favorites mode names the row: it carries a star, or a starred folder holds it.

        Being held by a starred folder is a fact about the path, so a reconstruction listed under the
        sample it came from answers the same as the row standing for it beside its configuration.
        """
        if self.logic.is_node_favorite(node):
            return True

        return isinstance(node, FileSystemNode) and self.logic.has_favorite_ancestor(node)

    def _is_anchored(self, node: TreeNode) -> bool:
        """Whether the mode points the reader at the row, which is what the way down opens to.

        A star sits on a row the reader marked, so that row is pointed at wherever it sits — inside
        another starred folder among the rest, which is what lets an explicit favorite open the folder
        above it. A row a starred folder merely holds is where the star first reaches only while no
        row above it is reached, which is how the sample branch answers: its headings carry no path,
        so the variants are where the star arrives.

        Asked of the rows the star reaches, so a row it declines stands under a row it named: the
        reader is pointed at the folder, and the rows inside it stand as they were.
        """
        if self.logic.is_node_favorite(node):
            return True

        parent = node.parent
        return parent is None or not self._is_starred(parent)
