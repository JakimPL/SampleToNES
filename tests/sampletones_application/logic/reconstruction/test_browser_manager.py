from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.reconstruction.browser_manager import BrowserManager


@pytest.fixture
def config_manager(tmp_path: Path) -> MagicMock:
    mock = MagicMock()
    mock.get_reconstructions_directory.return_value = tmp_path
    return mock


@pytest.fixture
def language_manager() -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = MagicMock(return_value="Reconstructions")
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
