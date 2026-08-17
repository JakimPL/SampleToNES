from typing import Dict

from sampletones_application.logic.reconstruction.browser.tree.configurations.branch import (
    build_configuration_branch,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_core.configs.display import (
    disambiguated_display_name,
    format_frequencies,
    format_transformation,
)
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import (
    ConfigNode,
    FileSystemNode,
    NodeType,
    TreeNode,
)

from .conftest import (
    BRANCH_NAME,
    HASH_A,
    HASH_B,
    RECONSTRUCTIONS,
    config_entry,
    config_fields,
    directory_children,
    file_children,
    group_children,
    plain_entry,
    reconstruction_entry,
    scan_of,
)


def build_branch(scan: ReconstructionScan) -> TreeNode:
    return build_configuration_branch(
        scan,
        name=BRANCH_NAME,
        parent=TreeNode("Root", node_type=NodeType.ROOT),
    )


def frequencies_name(fields: ConfigDirectoryFields) -> str:
    return format_frequencies(fields.sr, fields.nf)


def transformation_name(fields: ConfigDirectoryFields) -> str:
    return format_transformation(fields.sm, fields.tg)


def generator_directories(
    branch: TreeNode,
    fields: ConfigDirectoryFields,
) -> Dict[str, FileSystemNode]:
    frequencies_node = group_children(branch)[frequencies_name(fields)]
    return directory_children(group_children(frequencies_node)[transformation_name(fields)])


class TestTopLevelConfigDirectories:
    def test_config_directory_groups_by_frequencies_then_transformation(self) -> None:
        fields = config_fields(generators="PpT")
        branch = build_branch(scan_of(config_entry(fields, "song")))

        frequencies = group_children(branch)
        assert set(frequencies) == {frequencies_name(fields)}

        transformations = group_children(frequencies[frequencies_name(fields)])
        assert set(transformations) == {transformation_name(fields)}

        assert set(directory_children(transformations[transformation_name(fields)])) == {fields.gn}

    def test_config_directory_keeps_its_reconstructions(self) -> None:
        fields = config_fields()
        entry = config_entry(fields, "song")
        branch = build_branch(scan_of(entry))

        directory_node = generator_directories(branch, fields)[fields.gn]
        assert file_children(directory_node)["song"].filepath == entry.entries[0].path

    def test_config_directory_carries_its_parsed_configuration(self) -> None:
        fields = config_fields()
        branch = build_branch(scan_of(config_entry(fields, "song")))

        directory_node = generator_directories(branch, fields)[fields.gn]
        assert isinstance(directory_node, ConfigNode)
        assert directory_node.config == fields

    def test_colliding_generators_get_a_hash_suffix(self) -> None:
        first = config_fields(config_hash=HASH_A)
        second = config_fields(config_hash=HASH_B)
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        assert set(generator_directories(branch, first)) == {
            disambiguated_display_name(first.gn, HASH_A),
            disambiguated_display_name(second.gn, HASH_B),
        }

    def test_distinct_generators_share_a_transformation_group_under_their_own_names(self) -> None:
        first = config_fields(generators="PTN")
        second = config_fields(generators="TN")
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        assert set(generator_directories(branch, first)) == {"PTN", "TN"}

    def test_distinct_frequencies_form_separate_groups(self) -> None:
        first = config_fields(sample_rate=44100, nes_frequency=30)
        second = config_fields(sample_rate=48000, nes_frequency=60)
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        assert set(group_children(branch)) == {frequencies_name(first), frequencies_name(second)}

    def test_distinct_transformations_form_separate_groups(self) -> None:
        first = config_fields(spectrum_method=SpectrumMethod.FFT)
        second = config_fields(spectrum_method=SpectrumMethod.CQT)
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        transformations = group_children(group_children(branch)[frequencies_name(first)])
        assert set(transformations) == {transformation_name(first), transformation_name(second)}


class TestPlainFolders:
    def test_plain_folder_keeps_its_name_and_holds_its_reconstructions(self) -> None:
        entry = plain_entry("my_songs", reconstruction_entry(RECONSTRUCTIONS / "my_songs", "song"))
        branch = build_branch(scan_of(entry))

        directory_node = directory_children(branch)["my_songs"]
        assert set(file_children(directory_node)) == {"song"}

    def test_empty_folder_stays_in_place(self) -> None:
        branch = build_branch(scan_of(plain_entry("empty")))

        assert set(directory_children(branch)) == {"empty"}

    def test_nested_config_directory_takes_its_friendly_name(self) -> None:
        fields = config_fields()
        branch = build_branch(scan_of(plain_entry("my_songs", config_entry(fields, "song"))))

        nested = directory_children(directory_children(branch)["my_songs"])
        assert set(nested) == {fields.display_name}

    def test_colliding_nested_config_directories_get_a_hash_suffix(self) -> None:
        first = config_fields(config_hash=HASH_A)
        second = config_fields(config_hash=HASH_B)
        branch = build_branch(
            scan_of(plain_entry("my_songs", config_entry(first, "song"), config_entry(second, "song")))
        )

        nested = directory_children(directory_children(branch)["my_songs"])
        assert set(nested) == {
            disambiguated_display_name(first.display_name, HASH_A),
            disambiguated_display_name(second.display_name, HASH_B),
        }


class TestLooseReconstructions:
    def test_reconstruction_beside_the_config_directories_is_listed_here(self) -> None:
        entry = reconstruction_entry(RECONSTRUCTIONS, "song")
        branch = build_branch(scan_of(entry))

        assert file_children(branch)["song"].filepath == entry.path
