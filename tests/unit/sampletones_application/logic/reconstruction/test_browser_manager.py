from __future__ import annotations

from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.reconstruction.browser_manager import BrowserManager
from sampletones_core.structures.tree import FileSystemNode, NodeType, TreeNode

HASH_A = "6edf7c948606917a78b45d153c7ca7e0"
HASH_B = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def reconstructions_node(browser_manager: BrowserManager) -> TreeNode:
    root = browser_manager.tree.get_root()
    assert root is not None
    return group_children(root)["Reconstructions"]


def samples_node(browser_manager: BrowserManager) -> TreeNode:
    root = browser_manager.tree.get_root()
    assert root is not None
    return group_children(root)["Samples"]


def directory_nodes(browser_manager: BrowserManager) -> Dict[str, FileSystemNode]:
    return directory_children(reconstructions_node(browser_manager))


def directory_children(node: TreeNode) -> Dict[str, FileSystemNode]:
    return {
        child.name: child
        for child in node.children
        if isinstance(child, FileSystemNode) and child.node_type == NodeType.DIRECTORY
    }


def file_children(node: TreeNode) -> Dict[str, FileSystemNode]:
    return {
        child.name: child
        for child in node.children
        if isinstance(child, FileSystemNode) and child.node_type == NodeType.FILE
    }


def group_children(node: TreeNode) -> Dict[str, TreeNode]:
    return {
        child.name: child
        for child in node.children
        if isinstance(child, TreeNode) and child.node_type == NodeType.GROUP
    }


@pytest.fixture
def config_manager(tmp_path: Path) -> MagicMock:
    mock = MagicMock()
    mock.get_reconstructions_directory.return_value = tmp_path
    return mock


BROWSER_LABELS = {
    "global.browser.label.root": "Root",
    "global.browser.label.browser": "Browser",
    "global.browser.label.reconstructions": "Reconstructions",
    "global.browser.label.samples": "Samples",
}


@pytest.fixture
def language_manager() -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = MagicMock(side_effect=BROWSER_LABELS.__getitem__)
    return mock


@pytest.fixture
def browser_manager(config_manager: MagicMock, language_manager: MagicMock) -> BrowserManager:
    return BrowserManager(config_manager, language_manager=language_manager)


class TestBrowserManagerRefreshTree:
    def test_non_existent_directory_sets_root_to_none(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        browser_manager.reconstructions_directory = tmp_path / "does_not_exist"
        browser_manager.refresh_tree()
        assert browser_manager.tree.root is None

    def test_empty_directory_produces_empty_leaf_list(
        self,
        browser_manager: BrowserManager,
    ) -> None:
        browser_manager.refresh_tree()
        assert browser_manager.get_all_reconstruction_files() == []

    def test_stn_files_appear_as_leaves(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "song.stn").touch()
        browser_manager.refresh_tree()
        files = browser_manager.get_all_reconstruction_files()
        assert len(files) == 1
        assert files[0] == tmp_path / "song.stn"

    def test_non_stn_files_are_excluded(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "audio.wav").touch()
        (tmp_path / "song.stn").touch()
        browser_manager.refresh_tree()
        files = browser_manager.get_all_reconstruction_files()
        assert len(files) == 1
        assert all(f.suffix == ".stn" for f in files)

    def test_nested_stn_files_are_included(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "song.stn").touch()
        browser_manager.refresh_tree()
        files = browser_manager.get_all_reconstruction_files()
        assert len(files) == 1
        assert files[0] == subdir / "song.stn"

    def test_directory_with_only_non_stn_files_is_not_returned(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        subdir = tmp_path / "audio_only"
        subdir.mkdir()
        (subdir / "track.wav").touch()
        browser_manager.refresh_tree()
        assert browser_manager.get_all_reconstruction_files() == []

    def test_empty_subdirectory_is_not_returned(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "empty_dir").mkdir()
        browser_manager.refresh_tree()
        assert browser_manager.get_all_reconstruction_files() == []


class TestBrowserManagerFriendlyNames:
    def test_config_directory_groups_by_frequency_method_generators(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_PpT_ch_{HASH_A}"
        config_dir.mkdir()
        (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        reconstructions = reconstructions_node(browser_manager)
        frequencies = group_children(reconstructions)
        assert set(frequencies) == {"44.1 kHz·30 Hz"}

        methods = group_children(frequencies["44.1 kHz·30 Hz"])
        assert set(methods) == {"FFT·γ0"}

        assert set(directory_children(methods["FFT·γ0"])) == {"PpT"}

    def test_colliding_config_directories_get_hash_suffix(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for config_hash in (HASH_A, HASH_B):
            config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_PpT_ch_{config_hash}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        reconstructions = reconstructions_node(browser_manager)
        methods = group_children(group_children(reconstructions)["44.1 kHz·30 Hz"])
        assert set(directory_children(methods["FFT·γ0"])) == {
            f"PpT·#{HASH_A[:7]}",
            f"PpT·#{HASH_B[:7]}",
        }

    def test_distinct_frequencies_form_separate_groups(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for sample_rate, nes_frequency in ((44100, 30), (48000, 60)):
            config_dir = tmp_path / f"sr_{sample_rate}_nf_{nes_frequency}_sm_fft_tg_0_gn_PTN_ch_{HASH_A}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        assert set(group_children(reconstructions_node(browser_manager))) == {"44.1 kHz·30 Hz", "48 kHz·60 Hz"}

    def test_distinct_methods_form_separate_groups(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for spectrum_method in ("fft", "cqt"):
            config_dir = tmp_path / f"sr_44100_nf_30_sm_{spectrum_method}_tg_0_gn_PTN_ch_{HASH_A}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        methods = group_children(group_children(reconstructions_node(browser_manager))["44.1 kHz·30 Hz"])
        assert set(methods) == {"FFT·γ0", "CQT·γ0"}

    def test_distinct_generators_share_method_group_without_hash(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for generators in ("PTN", "TN"):
            config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_{generators}_ch_{HASH_A}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        methods = group_children(group_children(reconstructions_node(browser_manager))["44.1 kHz·30 Hz"])
        assert set(directory_children(methods["FFT·γ0"])) == {"PTN", "TN"}

    def test_non_config_directory_keeps_raw_name(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        plain = tmp_path / "my_songs"
        plain.mkdir()
        (plain / "song.stn").touch()

        browser_manager.refresh_tree()

        assert "my_songs" in directory_nodes(browser_manager)


class TestBrowserManagerSamplesView:
    def test_samples_are_grouped_by_source_directory_and_audio(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_{HASH_A}"
        audio_dir = config_dir / "Amen Breaks" / "Amen Breaks vol.1"
        audio_dir.mkdir(parents=True)
        (audio_dir / "cw_amen02_165.stn").touch()

        browser_manager.refresh_tree()

        samples = samples_node(browser_manager)
        amen_breaks = group_children(samples)["Amen Breaks"]
        amen_breaks_vol1 = group_children(amen_breaks)["Amen Breaks vol.1"]
        audio = group_children(amen_breaks_vol1)["cw_amen02_165"]
        variant = file_children(audio)["44.1 kHz·30 Hz·FFT·γ0·PTN"]
        assert variant.filepath == audio_dir / "cw_amen02_165.stn"

    def test_one_audio_lists_each_config_variant(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for spectrum_method in ("fft", "cqt"):
            config_dir = tmp_path / f"sr_44100_nf_30_sm_{spectrum_method}_tg_0_gn_PTN_ch_{HASH_A}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        audio = group_children(samples_node(browser_manager))["song"]
        assert set(file_children(audio)) == {
            "44.1 kHz·30 Hz·FFT·γ0·PTN",
            "44.1 kHz·30 Hz·CQT·γ0·PTN",
        }

    def test_colliding_variants_of_one_audio_get_hash_suffix(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        for config_hash in (HASH_A, HASH_B):
            config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_{config_hash}"
            config_dir.mkdir()
            (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        audio = group_children(samples_node(browser_manager))["song"]
        assert set(file_children(audio)) == {
            f"44.1 kHz·30 Hz·FFT·γ0·PTN·#{HASH_A[:7]}",
            f"44.1 kHz·30 Hz·FFT·γ0·PTN·#{HASH_B[:7]}",
        }

    def test_single_file_conversion_appears_at_samples_root(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        config_dir = tmp_path / f"sr_44100_nf_30_sm_fft_tg_0_gn_PTN_ch_{HASH_A}"
        config_dir.mkdir()
        (config_dir / "song.stn").touch()

        browser_manager.refresh_tree()

        samples = samples_node(browser_manager)
        assert set(group_children(samples)) == {"song"}
        assert set(file_children(group_children(samples)["song"])) == {"44.1 kHz·30 Hz·FFT·γ0·PTN"}

    def test_non_config_directory_is_excluded_from_samples(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        plain = tmp_path / "my_songs"
        plain.mkdir()
        (plain / "song.stn").touch()

        browser_manager.refresh_tree()

        assert group_children(samples_node(browser_manager)) == {}
        assert "my_songs" in directory_nodes(browser_manager)


class TestBrowserManagerSetDirectory:
    def test_set_reconstructions_directory_updates_directory(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        browser_manager.set_reconstructions_directory(new_dir)
        assert browser_manager.reconstructions_directory == new_dir

    def test_set_reconstructions_directory_triggers_refresh(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        new_dir = tmp_path / "populated"
        new_dir.mkdir()
        (new_dir / "track.stn").touch()
        browser_manager.set_reconstructions_directory(new_dir)
        assert len(browser_manager.get_all_reconstruction_files()) == 1


class TestBrowserManagerGetAllReconstructionFiles:
    def test_returns_paths_for_all_stn_leaves(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "a.stn").touch()
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "b.stn").touch()
        browser_manager.refresh_tree()
        files = browser_manager.get_all_reconstruction_files()
        assert len(files) == 2
        assert {f.name for f in files} == {"a.stn", "b.stn"}
