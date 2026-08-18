from sampletones_application.logic.reconstruction.browser.tree.order import order_children

from .conftest import (
    CONFIGURATION_BRANCH_KEY,
    SAMPLE_BRANCH_KEY,
    child_names,
    container_root,
    directory_node,
    file_node,
    group_node,
    sample_node,
)


class TestNameOrder:
    def test_numbers_read_as_numbers(self) -> None:
        """A frequency group sits by the value its label states, whatever the folder name spells."""
        root = container_root()
        branch = group_node("branch", root)
        for name in ("44.1 kHz·30 Hz", "8 kHz·60 Hz", "22.05 kHz·30 Hz"):
            group_node(name, branch)

        order_children(root)

        assert child_names(branch) == ["8 kHz·60 Hz", "22.05 kHz·30 Hz", "44.1 kHz·30 Hz"]

    def test_names_read_as_a_reader_reads_them(self) -> None:
        """A capital letter states nothing about order, so names read alphabetically as they look."""
        root = container_root()
        branch = group_node("branch", root)
        for name in ("Beats", "amen", "Cymbals"):
            sample_node(name, branch)

        order_children(root)

        assert child_names(branch) == ["amen", "Beats", "Cymbals"]

    def test_order_reaches_every_level(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        sample = sample_node("song", branch)
        for name in ("FFT·γ0", "CQT·γ0"):
            file_node(name, sample)

        order_children(root)

        assert child_names(sample) == ["CQT·γ0", "FFT·γ0"]


class TestContainersFirst:
    def test_folders_and_groups_precede_reconstructions(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        file_node("aaa", branch)
        group_node("zzz group", branch)
        directory_node("zzz folder", branch)
        sample_node("zzz sample", branch)

        order_children(root)

        assert child_names(branch) == ["zzz folder", "zzz group", "zzz sample", "aaa"]


class TestBranches:
    def test_branches_keep_the_order_the_browser_states(self) -> None:
        """The two views read in the order they are built, rather than by the labels they carry."""
        root = container_root()
        group_node(CONFIGURATION_BRANCH_KEY, root)
        group_node(SAMPLE_BRANCH_KEY, root)

        order_children(root)

        assert child_names(root) == [CONFIGURATION_BRANCH_KEY, SAMPLE_BRANCH_KEY]


class TestSubtrees:
    def test_reordered_rows_keep_what_they_hold(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        second = group_node("second", branch)
        file_node("song", second)
        group_node("first", branch)

        order_children(root)

        assert child_names(branch) == ["first", "second"]
        assert child_names(second) == ["song"]
        assert second.parent is branch
