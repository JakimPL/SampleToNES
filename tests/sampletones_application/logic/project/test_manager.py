from pathlib import Path

from sampletones_application.logic.project.manager import ProjectManager
from sampletones_core.constants.enums import GeneratorName


class TestProjectManager:
    def test_starts_with_a_clean_default_project(self) -> None:
        manager = ProjectManager()
        assert set(manager.current.song.channels) == set(GeneratorName.items())
        assert len(manager.current.instruments) == 0
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
        assert len(manager.current.instruments) == 0

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
