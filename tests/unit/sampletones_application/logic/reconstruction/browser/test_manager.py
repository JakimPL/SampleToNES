from pathlib import Path
from typing import Iterator, List

import pytest

from sampletones_application.logic.reconstruction.browser.manager import BrowserManager

from .conftest import (
    CONFIGURATION_BRANCH_KEY,
    SAMPLE_BRANCH_KEY,
    config_directory,
    config_fields,
    configuration_branch,
    file_children,
    group_children,
    sample_branch,
    sample_children,
    write_reconstruction,
)


class TestRefreshTree:
    def test_missing_directory_leaves_no_root(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        browser_manager.reconstructions_directory = tmp_path / "does_not_exist"
        browser_manager.refresh_tree()
        assert browser_manager.tree.root is None

    def test_root_holds_both_branches(self, browser_manager: BrowserManager) -> None:
        browser_manager.refresh_tree()

        root = browser_manager.tree.get_root()
        assert root is not None
        assert list(group_children(root)) == [CONFIGURATION_BRANCH_KEY, SAMPLE_BRANCH_KEY]

    def test_reconstruction_is_reachable_from_both_branches(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        fields = config_fields()
        path = write_reconstruction(config_directory(tmp_path, fields), "song")

        browser_manager.refresh_tree()

        configurations = configuration_branch(browser_manager)
        frequencies = next(iter(group_children(configurations).values()))
        methods = next(iter(group_children(frequencies).values()))
        generators = next(iter(methods.children))
        assert file_children(generators)["song"].filepath == path

        samples = sample_branch(browser_manager)
        assert file_children(sample_children(samples)["song"])[fields.display_name].filepath == path

    def test_reads_every_folder_once(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Both branches are built from one reading, so no folder is listed twice per refresh."""
        directory = config_directory(tmp_path, config_fields())
        write_reconstruction(directory, "Amen Breaks", "cw_amen02_165")

        listed: List[Path] = []
        original_iterdir = Path.iterdir

        def counting_iterdir(directory_path: Path) -> Iterator[Path]:
            listed.append(directory_path)
            return original_iterdir(directory_path)

        monkeypatch.setattr(Path, "iterdir", counting_iterdir)
        browser_manager.refresh_tree()

        assert tmp_path in listed
        assert sorted(listed) == sorted(set(listed))


class TestSetReconstructionsDirectory:
    def test_directory_is_taken_over(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        directory = tmp_path / "new"
        directory.mkdir()
        browser_manager.set_reconstructions_directory(directory)
        assert browser_manager.reconstructions_directory == directory

    def test_directory_change_refreshes_the_tree(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        directory = tmp_path / "populated"
        directory.mkdir()
        write_reconstruction(directory, "track")

        browser_manager.set_reconstructions_directory(directory)

        assert len(browser_manager.get_all_reconstruction_files()) == 1


class TestGetAllReconstructionFiles:
    def test_empty_directory_holds_no_reconstructions(self, browser_manager: BrowserManager) -> None:
        browser_manager.refresh_tree()
        assert browser_manager.get_all_reconstruction_files() == []

    def test_missing_directory_holds_no_reconstructions(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        browser_manager.reconstructions_directory = tmp_path / "does_not_exist"
        browser_manager.refresh_tree()
        assert browser_manager.get_all_reconstruction_files() == []

    def test_reconstructions_are_answered_in_path_order(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        root_path = write_reconstruction(tmp_path, "a")
        nested_path = write_reconstruction(tmp_path / "sub", "b")

        browser_manager.refresh_tree()

        assert browser_manager.get_all_reconstruction_files() == sorted([root_path, nested_path])

    def test_other_files_stay_out(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "audio.wav").touch()
        path = write_reconstruction(tmp_path, "song")

        browser_manager.refresh_tree()

        assert browser_manager.get_all_reconstruction_files() == [path]

    def test_folder_without_reconstructions_contributes_nothing(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        audio_only = tmp_path / "audio_only"
        audio_only.mkdir()
        (audio_only / "track.wav").touch()
        (tmp_path / "empty").mkdir()

        browser_manager.refresh_tree()

        assert browser_manager.get_all_reconstruction_files() == []

    def test_reconstruction_in_both_branches_is_answered_once(
        self,
        browser_manager: BrowserManager,
        tmp_path: Path,
    ) -> None:
        path = write_reconstruction(config_directory(tmp_path, config_fields()), "song")

        browser_manager.refresh_tree()

        assert browser_manager.get_all_reconstruction_files() == [path]
