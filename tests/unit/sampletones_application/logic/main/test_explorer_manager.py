from pathlib import Path
from typing import AbstractSet, Dict, List, Optional, Set

import pytest

from sampletones_application.logic.main.explorer_manager import ExplorerManager
from sampletones_core.structures.tree import FileSystemNode, Tree
from tests.suite.language import FakeLanguageManager

MUSIC = "music"
DRUMS = "drums"
NOTES = "notes"


class FakeConfigManager:
    """Answers the directories the explorer reveals, which a test points at its own corpus."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def get_library_directory(self) -> Path:
        return self._directory

    def get_reconstructions_directory(self) -> Path:
        return self._directory


def write_corpus(root: Path) -> Dict[str, Path]:
    """A folder holding a folder, beside a folder of its own, each carrying a file to be listed."""
    paths = {
        MUSIC: root / MUSIC,
        DRUMS: root / MUSIC / DRUMS,
        NOTES: root / NOTES,
    }
    for path in paths.values():
        path.mkdir(parents=True)
        (path / "song.wav").touch()

    return paths


def build_manager(
    root: Path,
    open_directories: AbstractSet[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> ExplorerManager:
    """An explorer reading one directory as its whole filesystem, so a test states every folder."""
    manager = ExplorerManager(
        FakeConfigManager(root),  # type: ignore[arg-type]
        language_manager=FakeLanguageManager(),
        open_directories=open_directories,
    )
    monkeypatch.setattr(manager, "_get_filesystems", lambda: [root], raising=False)
    return manager


def row_at(tree: Tree, path: Path) -> Optional[FileSystemNode]:
    rows = tree.find_nodes(FileSystemNode, lambda node: node.filepath == path)
    return rows[0] if rows else None


def rows_below(tree: Tree, path: Path) -> List[str]:
    row = row_at(tree, path)
    assert row is not None
    return sorted(str(child.name) for child in row.children)


class TestTheShapeASessionLeft:
    """The folders standing open are handed back at startup, and read down to on the next refresh."""

    def test_a_remembered_folder_comes_back_open(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, {paths[MUSIC]}, monkeypatch)

        manager.refresh_tree()

        assert manager.is_directory_open(paths[MUSIC])
        assert rows_below(manager.tree, paths[MUSIC]) == [DRUMS, "song.wav"]

    def test_a_folder_nested_in_a_remembered_one_is_read_down_to(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A row stands for every folder above the remembered one, which is what shows it."""
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, {paths[DRUMS]}, monkeypatch)

        manager.refresh_tree()

        assert manager.is_directory_open(paths[MUSIC])
        assert rows_below(manager.tree, paths[DRUMS]) == ["song.wav"]

    def test_a_folder_no_session_left_open_stays_folded(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, {paths[MUSIC]}, monkeypatch)

        manager.refresh_tree()

        assert not manager.is_directory_open(paths[NOTES])
        assert rows_below(manager.tree, paths[NOTES]) == []

    def test_a_folder_the_disk_has_lost_is_dropped_at_startup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        gone = tmp_path / "gone"

        manager = build_manager(tmp_path, {paths[MUSIC], gone}, monkeypatch)

        assert manager.open_directories == {paths[MUSIC]}

    def test_a_file_standing_where_a_folder_was_is_dropped_at_startup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_corpus(tmp_path)
        replaced = tmp_path / "replaced"
        replaced.touch()

        manager = build_manager(tmp_path, {replaced}, monkeypatch)

        assert manager.open_directories == set()


class TestReadingApartFromStandingOpen:
    """A folder read once and then folded away is loaded and closed, and comes back closed."""

    def test_a_folded_folder_keeps_the_children_it_read(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, set(), monkeypatch)
        manager.refresh_tree()
        music = row_at(manager.tree, paths[MUSIC])
        assert music is not None

        manager.expand_directory(music)
        manager.set_directory_open(paths[MUSIC], False)

        assert manager.has_loaded_children(paths[MUSIC])
        assert not manager.is_directory_open(paths[MUSIC])

    def test_a_refresh_brings_a_folded_folder_back_folded(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, set(), monkeypatch)
        manager.refresh_tree()
        music = row_at(manager.tree, paths[MUSIC])
        assert music is not None
        manager.expand_directory(music)
        manager.set_directory_open(paths[MUSIC], True)
        manager.set_directory_open(paths[MUSIC], False)

        manager.refresh_tree()

        assert not manager.is_directory_open(paths[MUSIC])

    def test_the_filesystem_the_tree_opens_at_stands_open(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        write_corpus(tmp_path)
        manager = build_manager(tmp_path, set(), monkeypatch)

        manager.refresh_tree()

        assert manager.is_directory_open(tmp_path)


class TestCollapseAll:
    def test_every_folder_is_folded_and_what_was_read_is_dropped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, {paths[DRUMS]}, monkeypatch)
        manager.refresh_tree()

        manager.collapse_all()

        assert manager.open_directories == set()
        assert not manager.has_loaded_children(paths[MUSIC])
        assert rows_below(manager.tree, tmp_path) == []


class TestTheShapeASaveReads:
    def test_the_folders_standing_open_are_answered_apart_from_the_explorer(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The explorer keeps writing its own shape, so what a save carries is a reading of it."""
        paths = write_corpus(tmp_path)
        manager = build_manager(tmp_path, {paths[MUSIC]}, monkeypatch)
        manager.refresh_tree()
        written: Set[Path] = manager.open_directories

        manager.set_directory_open(paths[MUSIC], False)

        assert paths[MUSIC] in written
        assert paths[MUSIC] not in manager.open_directories
