from sampletones_application.logic.reconstruction.browser.tree.prune import (
    prune_empty_containers,
)
from sampletones_core.structures.tree import NodeType

from .conftest import (
    child_names,
    container_root,
    directory_node,
    file_node,
    group_node,
    sample_node,
)


class TestEmptyContainers:
    def test_group_holding_nothing_leaves(self) -> None:
        root = container_root()
        group_node("44.1 kHz·30 Hz", root)

        prune_empty_containers(root)

        assert root.children == ()

    def test_sample_holding_nothing_leaves(self) -> None:
        root = container_root()
        sample_node("cw_amen02_165", root)

        prune_empty_containers(root)

        assert root.children == ()

    def test_a_whole_chain_of_empty_containers_leaves(self) -> None:
        """The deepest rows go first, so a heading emptied by its own children goes with them."""
        root = container_root()
        branch = group_node("branch", root)
        sample_node("cw_amen02_165", group_node("Amen Breaks", branch))

        prune_empty_containers(root)

        assert root.children == ()

    def test_the_container_root_stays(self) -> None:
        root = container_root()
        group_node("branch", root)

        prune_empty_containers(root)

        assert root.node_type == NodeType.ROOT
        assert root.parent is None


class TestGatheringContainers:
    def test_group_holding_a_reconstruction_stays(self) -> None:
        root = container_root()
        file_node("song", group_node("branch", root))

        prune_empty_containers(root)

        assert child_names(root) == ["branch"]

    def test_sample_holding_its_variants_stays(self) -> None:
        root = container_root()
        sample = sample_node("song", root)
        file_node("44.1 kHz·30 Hz·FFT·γ0·PTN", sample)

        prune_empty_containers(root)

        assert child_names(root) == ["song"]
        assert child_names(sample) == ["44.1 kHz·30 Hz·FFT·γ0·PTN"]

    def test_a_branch_keeps_the_containers_leading_to_a_reconstruction(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        kept = group_node("Amen Breaks", branch)
        file_node("song", sample_node("cw_amen02_165", kept))
        group_node("Beats", branch)

        prune_empty_containers(root)

        assert child_names(branch) == ["Amen Breaks"]
        assert child_names(kept) == ["cw_amen02_165"]


class TestFolders:
    def test_folder_holding_nothing_stays(self) -> None:
        """The configuration branch reads the disk as it is, so an empty folder is still a folder."""
        root = container_root()
        branch = group_node("branch", root)
        directory_node("empty", branch)

        prune_empty_containers(root)

        assert child_names(branch) == ["empty"]

    def test_group_holding_only_an_empty_folder_stays(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        directory_node("empty", group_node("44.1 kHz·30 Hz", branch))

        prune_empty_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz"]
