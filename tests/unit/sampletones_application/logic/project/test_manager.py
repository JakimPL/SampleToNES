from pathlib import Path

import pytest

from sampletones_application.logic.project.manager import ProjectManager
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.exceptions import NotAValidArchiveError


class TestProjectManager:
    def test_starts_with_a_clean_default_project(self) -> None:
        manager = ProjectManager()
        assert set(manager.current.song.channels) == set(GeneratorName.items())
        assert len(manager.current.samples) == 0
        assert manager.is_dirty is False

    def test_mark_updated_sets_dirty(self) -> None:
        manager = ProjectManager()
        manager.mark_updated()
        assert manager.is_dirty is True

    def test_new_replaces_with_clean_project(self) -> None:
        manager = ProjectManager()
        manager.mark_updated()
        manager.new()
        assert manager.is_dirty is False
        assert len(manager.current.samples) == 0

    def test_save_load_round_trip(self, tmp_path: Path) -> None:
        manager = ProjectManager()
        manager.current.info.title = "Demo"
        manager.mark_updated()

        path = tmp_path / "demo.stp"
        manager.save(path)
        assert manager.is_dirty is False
        assert manager.name == "demo"

        loaded = ProjectManager()
        loaded.load(path)
        assert loaded.name == "demo"
        assert loaded.is_dirty is False
        assert loaded.current.info.title == "Demo"
        assert set(loaded.current.song.channels) == set(GeneratorName.items())


class TestLoadPropagatesErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ProjectManager().load(tmp_path / "nope.stp")

    def test_directory_raises_is_a_directory(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError):
            ProjectManager().load(tmp_path)

    def test_invalid_archive_raises_load_project_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.stp"
        path.write_bytes(b"this is not a zip archive")

        with pytest.raises(NotAValidArchiveError):
            ProjectManager().load(path)
