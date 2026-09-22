from sampletones_application.logic.reconstruction.browser.tree.collapse import (
    collapse_single_child_containers,
)
from sampletones_core.structures.tree import NodeType

from .conftest import (
    child_names,
    config_group_node,
    config_variant_node,
    container_root,
    directory_node,
    file_node,
    group_node,
    sample_node,
)


class TestLoneHeadings:
    def test_a_group_leading_to_one_row_folds_into_it(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        file_node("song", group_node("44.1 kHz·30 Hz", branch))

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz·song"]

    def test_a_chain_folds_into_one_row(self) -> None:
        """The deepest heading folds first, so each level it passes adds one separator."""
        root = container_root()
        branch = group_node("branch", root)
        frequencies = group_node("44.1 kHz·30 Hz", branch)
        file_node("song", group_node("FFT·γ0", frequencies))

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz·FFT·γ0·song"]

    def test_a_sample_leading_to_one_variant_folds_into_it(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        file_node("44.1 kHz·30 Hz·FFT·γ0·PTN", sample_node("cw_amen02_165", branch))

        collapse_single_child_containers(root)

        assert child_names(branch) == ["cw_amen02_165·44.1 kHz·30 Hz·FFT·γ0·PTN"]

    def test_the_folded_row_keeps_what_it_carries(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        reconstruction = file_node("song", group_node("44.1 kHz·30 Hz", branch))
        held = reconstruction.filepath

        collapse_single_child_containers(root)

        folded = branch.children[0]
        assert folded is reconstruction
        assert folded.node_type == NodeType.FILE
        assert folded.filepath == held

    def test_a_folded_group_keeps_the_children_it_led_to(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        directory = directory_node("Amen Breaks", group_node("44.1 kHz·30 Hz", branch))
        file_node("song", directory)

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz·Amen Breaks"]
        assert child_names(directory) == ["song"]


class TestWhatAFoldedNameStates:
    def test_a_sample_leaves_the_variant_reading_as_a_plain_name(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        variant = config_variant_node("44.1 kHz·30 Hz·FFT·γ0·PTN", sample_node("cw_amen02_165", branch))

        collapse_single_child_containers(root)

        assert not variant.states_configuration

    def test_a_chain_of_configuration_headings_still_states_a_configuration(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        frequencies = config_group_node("44.1 kHz·30 Hz", branch)
        variant = config_variant_node("PTN", config_group_node("FFT·γ0", frequencies))

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz·FFT·γ0·PTN"]
        assert variant.states_configuration

    def test_a_source_folder_above_a_folded_variant_leaves_it_plain(self) -> None:
        """Deepest first, the sample folds in and then the folder does, and one plain name is enough."""
        root = container_root()
        branch = group_node("branch", root)
        folder = group_node("Amen Breaks", branch)
        variant = config_variant_node("44.1 kHz·30 Hz·FFT·γ0·PTN", sample_node("cw_amen02_165", folder))

        collapse_single_child_containers(root)

        assert child_names(branch) == ["Amen Breaks·cw_amen02_165·44.1 kHz·30 Hz·FFT·γ0·PTN"]
        assert not variant.states_configuration

    def test_a_variant_no_heading_folded_into_states_its_configuration(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        sample = sample_node("cw_amen02_165", branch)
        variant = config_variant_node("44.1 kHz·30 Hz·FFT·γ0·PTN", sample)
        config_variant_node("44.1 kHz·60 Hz·FFT·γ0·PTN", sample)

        collapse_single_child_containers(root)

        assert variant.states_configuration


class TestHeadingsThatStay:
    def test_a_group_gathering_several_rows_stays(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        frequencies = group_node("44.1 kHz·30 Hz", branch)
        file_node("first", frequencies)
        file_node("second", frequencies)

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz"]
        assert child_names(frequencies) == ["first", "second"]

    def test_a_branch_root_stays(self) -> None:
        """Each branch names a way of reading the whole tree, so it heads its rows however few they are."""
        root = container_root()
        branch = group_node("branch", root)
        file_node("song", branch)

        collapse_single_child_containers(root)

        assert child_names(root) == ["branch"]
        assert child_names(branch) == ["song"]

    def test_a_folder_leading_to_one_row_stays(self) -> None:
        """The configuration branch mirrors the disk, so a folder holding one file is still a folder."""
        root = container_root()
        branch = group_node("branch", root)
        directory = directory_node("Amen Breaks", branch)
        file_node("song", directory)

        collapse_single_child_containers(root)

        assert child_names(branch) == ["Amen Breaks"]
        assert child_names(directory) == ["song"]

    def test_a_group_whose_fold_would_repeat_a_name_beside_it_stays(self) -> None:
        root = container_root()
        branch = group_node("branch", root)
        frequencies = group_node("44.1 kHz·30 Hz", branch)
        file_node("song", frequencies)
        file_node("44.1 kHz·30 Hz·song", branch)

        collapse_single_child_containers(root)

        assert child_names(branch) == ["44.1 kHz·30 Hz", "44.1 kHz·30 Hz·song"]
        assert child_names(frequencies) == ["song"]

    def test_the_container_root_stays(self) -> None:
        root = container_root()
        file_node("song", group_node("branch", root))

        collapse_single_child_containers(root)

        assert root.node_type == NodeType.ROOT
        assert root.parent is None
        assert child_names(root) == ["branch"]
