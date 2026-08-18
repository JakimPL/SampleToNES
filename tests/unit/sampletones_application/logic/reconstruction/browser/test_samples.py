from sampletones_application.logic.reconstruction.browser.tree.entries.directory import (
    DirectoryEntry,
)
from sampletones_application.logic.reconstruction.browser.tree.entries.scan import (
    ReconstructionScan,
)
from sampletones_application.logic.reconstruction.browser.tree.samples.branch import (
    build_sample_branch,
)
from sampletones_core.configs.display import disambiguated_display_name
from sampletones_core.constants.enums import SpectrumMethod
from sampletones_core.structures.tree import ConfigNode, NodeType, TreeNode

from .conftest import (
    BRANCH_NAME,
    HASH_A,
    HASH_B,
    RECONSTRUCTIONS,
    config_entry,
    config_fields,
    file_children,
    group_children,
    plain_entry,
    reconstruction_entry,
    sample_children,
    scan_of,
)


def build_branch(scan: ReconstructionScan) -> TreeNode:
    return build_sample_branch(
        scan,
        name=BRANCH_NAME,
        parent=TreeNode("Root", node_type=NodeType.ROOT),
    )


class TestSampleGrouping:
    def test_audio_appears_under_the_folders_it_came_from(self) -> None:
        fields = config_fields()
        directory = RECONSTRUCTIONS / fields.directory_name
        entry = DirectoryEntry(
            path=directory,
            config=fields,
            entries=(reconstruction_entry(directory, "Amen Breaks", "vol.1", "cw_amen02_165"),),
        )
        branch = build_branch(scan_of(entry))

        amen_breaks = group_children(branch)["Amen Breaks"]
        volume = group_children(amen_breaks)["vol.1"]
        audio_node = sample_children(volume)["cw_amen02_165"]
        assert file_children(audio_node)[fields.display_name].filepath == entry.entries[0].path

    def test_audio_at_the_root_of_a_config_directory_appears_at_the_branch_root(self) -> None:
        fields = config_fields()
        branch = build_branch(scan_of(config_entry(fields, "song")))

        assert set(sample_children(branch)) == {"song"}
        assert set(file_children(sample_children(branch)["song"])) == {fields.display_name}

    def test_one_audio_lists_every_configuration_that_reconstructed_it(self) -> None:
        first = config_fields(spectrum_method=SpectrumMethod.FFT)
        second = config_fields(spectrum_method=SpectrumMethod.CQT)
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        audio_node = sample_children(branch)["song"]
        assert set(file_children(audio_node)) == {first.display_name, second.display_name}

    def test_each_audio_gathers_only_its_own_variants(self) -> None:
        fields = config_fields()
        branch = build_branch(scan_of(config_entry(fields, "first", "second")))

        assert set(sample_children(branch)) == {"first", "second"}
        for audio_name in ("first", "second"):
            assert set(file_children(sample_children(branch)[audio_name])) == {fields.display_name}

    def test_colliding_variants_of_one_audio_get_a_hash_suffix(self) -> None:
        first = config_fields(config_hash=HASH_A)
        second = config_fields(config_hash=HASH_B)
        branch = build_branch(scan_of(config_entry(first, "song"), config_entry(second, "song")))

        audio_node = sample_children(branch)["song"]
        assert set(file_children(audio_node)) == {
            disambiguated_display_name(first.display_name, HASH_A),
            disambiguated_display_name(second.display_name, HASH_B),
        }


class TestSampleNodeTypes:
    def test_audio_is_a_sample_and_the_folder_above_it_is_a_group(self) -> None:
        fields = config_fields()
        directory = RECONSTRUCTIONS / fields.directory_name
        entry = DirectoryEntry(
            path=directory,
            config=fields,
            entries=(reconstruction_entry(directory, "Amen Breaks", "cw_amen02_165"),),
        )
        branch = build_branch(scan_of(entry))

        folder_node = group_children(branch)["Amen Breaks"]
        assert folder_node.node_type == NodeType.GROUP
        assert sample_children(folder_node)["cw_amen02_165"].node_type == NodeType.SAMPLE

    def test_a_folder_and_the_audio_beside_it_stay_two_rows(self) -> None:
        """A configuration directory holding ``song.stn`` beside ``song/inner.stn`` lists both.

        The folder gathers what it holds while the audio gathers its variants, each row found among
        the siblings of its own kind.
        """
        fields = config_fields()
        directory = RECONSTRUCTIONS / fields.directory_name
        entry = DirectoryEntry(
            path=directory,
            config=fields,
            entries=(
                DirectoryEntry(
                    path=directory / "song",
                    config=None,
                    entries=(reconstruction_entry(directory, "song", "inner"),),
                ),
                reconstruction_entry(directory, "song"),
            ),
        )
        branch = build_branch(scan_of(entry))

        assert set(group_children(branch)) == {"song"}
        assert set(sample_children(branch)) == {"song"}
        assert set(sample_children(group_children(branch)["song"])) == {"inner"}
        assert set(file_children(sample_children(branch)["song"])) == {fields.display_name}


class TestSampleVariants:
    def test_variant_carries_the_configuration_of_its_directory(self) -> None:
        """A leaf in the sample view states the configuration its directory names.

        Its own filename is the audio name, so the configuration reaches the tooltip and the
        configuration font from the node rather than from the path.
        """
        fields = config_fields()
        branch = build_branch(scan_of(config_entry(fields, "song")))

        variant = next(iter(file_children(sample_children(branch)["song"]).values()))
        assert isinstance(variant, ConfigNode)
        assert variant.config == fields


class TestSampleSources:
    def test_folder_stating_no_configuration_stays_out(self) -> None:
        entry = plain_entry("my_songs", reconstruction_entry(RECONSTRUCTIONS / "my_songs", "song"))
        branch = build_branch(scan_of(entry))

        assert branch.children == ()

    def test_reconstruction_beside_the_config_directories_stays_out(self) -> None:
        branch = build_branch(scan_of(reconstruction_entry(RECONSTRUCTIONS, "song")))

        assert branch.children == ()
