from pathlib import Path
from typing import List, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.reconstruction.browser.tree.collapse import (
    collapse_single_child_containers,
)
from sampletones_application.logic.reconstruction.browser.tree.configurations.branch import (
    build_configuration_branch,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_application.logic.reconstruction.browser.tree.order import order_children
from sampletones_application.logic.reconstruction.browser.tree.prune import (
    prune_empty_containers,
)
from sampletones_application.logic.reconstruction.browser.tree.samples.branch import (
    build_sample_branch,
)
from sampletones_application.logic.reconstruction.browser.tree.scan import (
    scan_reconstructions,
)
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree, TreeNode


class BrowserManager:
    """Owns the reconstruction browser tree, rebuilt from one reading of the reconstructions directory.

    A refresh scans the directory, builds the configuration branch and the sample branch from that
    one reading, shapes what came out — empty headings pruned, lone headings folded into the row they
    lead to, siblings ordered — and publishes the result as the tree both browser tabs render.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._language_manager = language_manager
        self.config_manager = config_manager
        self.reconstructions_directory = config_manager.get_reconstructions_directory()

        self.tree = Tree()
        self._scan = ReconstructionScan(entries=())

    def set_reconstructions_directory(self, directory: Path) -> None:
        self.reconstructions_directory = directory
        self.refresh_tree()

    def refresh_tree(self) -> None:
        if not self.reconstructions_directory.is_dir():
            self._scan = ReconstructionScan(entries=())
            self.tree.set_root(None)
            return

        self._scan = scan_reconstructions(self.reconstructions_directory)
        self.tree.set_root(self._build_root(self._scan))

    def _build_root(self, scan: ReconstructionScan) -> TreeNode:
        container_root = TreeNode(
            name=self._language_manager["global.browser.label.root"],
            node_type=NodeType.ROOT,
        )
        build_configuration_branch(
            scan,
            name=self._language_manager["global.browser.label.by_configuration"],
            parent=container_root,
        )
        build_sample_branch(
            scan,
            name=self._language_manager["global.browser.label.by_sample"],
            parent=container_root,
        )

        prune_empty_containers(container_root)
        collapse_single_child_containers(container_root)
        order_children(container_root)
        return container_root

    def get_all_reconstruction_files(self) -> List[Path]:
        return sorted({entry.path for entry in self._scan.reconstructions})

    def nodes_at(self, filepath: Path) -> Tuple[FileSystemNode, ...]:
        """Answers every row the browser offers for a path, across both views.

        A reconstruction is listed by its configuration and again by the sample it came from, so a
        caller acting on the file rather than on one row — repainting a favorite star, for instance —
        asks here once and hands the rows to each browser tab.
        """
        return self.tree.find_nodes(FileSystemNode, lambda node: node.filepath == filepath)
