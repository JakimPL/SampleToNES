from pathlib import Path
from typing import List, Optional

import pytest

from sampletones_application.logic.project.manager import ProjectManager
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.project import Project
from sampletones_shared.exceptions import NotAValidArchiveError
from tests.suite.errors import DIRECTORY_READ_ERRORS


class TestProjectManager:
    def test_starts_with_a_clean_default_project(self) -> None:
        manager = ProjectManager()
        assert set(manager.current.song.channels) == set(ChannelName.items())
        assert len(manager.current.voices) == 0
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
        assert len(manager.current.voices) == 0

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
        assert set(loaded.current.song.channels) == set(ChannelName.items())


class TestLoadPropagatesErrors:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            ProjectManager().load(tmp_path / "nope.stp")

    def test_directory_raises_directory_read_error(self, tmp_path: Path) -> None:
        with pytest.raises(DIRECTORY_READ_ERRORS):
            ProjectManager().load(tmp_path)

    def test_invalid_archive_raises_load_project_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.stp"
        path.write_bytes(b"this is not a zip archive")

        with pytest.raises(NotAValidArchiveError):
            ProjectManager().load(path)


class TestTheFileAProjectStandsFor:
    """The open project stands for the file it was last loaded from or saved to.

    A new or closed project stands for none, a failed load leaves the open project's file as it was,
    and each new file is reported once.
    """

    @pytest.fixture(name="reported")
    def reported_fixture(self) -> List[Optional[Path]]:
        return []

    @pytest.fixture(name="manager")
    def manager_fixture(self, reported: List[Optional[Path]]) -> ProjectManager:
        manager = ProjectManager()
        manager.on_path_changed = reported.append
        return manager

    @pytest.fixture(name="saved_project")
    def saved_project_fixture(self, tmp_path: Path) -> Path:
        path = tmp_path / "song.stp"
        ProjectManager().save(path)
        return path

    def test_a_fresh_manager_stands_for_no_file(self, manager: ProjectManager) -> None:
        assert manager.path is None

    def test_a_loaded_project_stands_for_its_file(
        self,
        manager: ProjectManager,
        saved_project: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)

        assert manager.path == saved_project
        assert reported == [saved_project]

    def test_a_saved_project_stands_for_the_file_it_was_saved_to(
        self,
        manager: ProjectManager,
        saved_project: Path,
        tmp_path: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)
        copy = tmp_path / "copy.stp"

        manager.save(copy)

        assert manager.path == copy
        assert reported == [saved_project, copy]

    def test_saving_again_to_its_file_reports_nothing_new(
        self,
        manager: ProjectManager,
        saved_project: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)

        manager.save(saved_project)

        assert reported == [saved_project]

    def test_a_new_project_stands_for_no_file(
        self,
        manager: ProjectManager,
        saved_project: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)

        manager.new()

        assert manager.path is None
        assert reported == [saved_project, None]

    def test_a_closed_project_stands_for_no_file(
        self,
        manager: ProjectManager,
        saved_project: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)

        manager.close()

        assert manager.path is None
        assert reported == [saved_project, None]

    def test_a_failed_load_keeps_the_open_project_s_file(
        self,
        manager: ProjectManager,
        saved_project: Path,
        tmp_path: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)
        broken = tmp_path / "broken.stp"
        broken.write_bytes(b"this is not a zip archive")

        with pytest.raises(NotAValidArchiveError):
            manager.load(broken)

        assert manager.path == saved_project
        assert reported == [saved_project]

    def test_a_history_restore_keeps_the_file(
        self,
        manager: ProjectManager,
        saved_project: Path,
        reported: List[Optional[Path]],
    ) -> None:
        manager.load(saved_project)

        manager.install(Project.create(), clean=False)

        assert manager.path == saved_project
        assert reported == [saved_project]
