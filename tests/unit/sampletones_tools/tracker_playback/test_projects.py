from pathlib import Path
from typing import Final, Set

import pytest

from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_shared.exceptions.project import NotAValidArchiveError
from sampletones_tools.tracker_playback.projects import (
    COUNTED_NAME,
    FIRST_COUNT,
    LOADED_PURPOSE,
    loaded_projects,
    unique_name,
)

FIRST_TITLE: Final[str] = "First song"
SECOND_TITLE: Final[str] = "Second song"


def _saved(path: Path, title: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ProjectContainer.save(Project.create(title=title), path)
    return path


class TestLoadedProjects:
    def test_each_file_becomes_a_project_named_after_it_in_the_order_given(self, tmp_path: Path) -> None:
        second = _saved(tmp_path / "second.stp", SECOND_TITLE)
        first = _saved(tmp_path / "first.stp", FIRST_TITLE)

        projects = loaded_projects((second, first))

        assert [project.name for project in projects] == ["second", "first"]
        assert [project.project.info.title for project in projects] == [SECOND_TITLE, FIRST_TITLE]

    def test_a_project_says_which_file_it_came_from(self, tmp_path: Path) -> None:
        path = _saved(tmp_path / "song.stp", FIRST_TITLE)

        (project,) = loaded_projects((path,))

        assert project.purpose == LOADED_PURPOSE.format(path=path.resolve())

    def test_files_sharing_a_name_write_apart(self, tmp_path: Path) -> None:
        first = _saved(tmp_path / "one" / "song.stp", FIRST_TITLE)
        second = _saved(tmp_path / "two" / "song.stp", SECOND_TITLE)

        projects = loaded_projects((first, second))

        assert [project.name for project in projects] == [
            "song",
            COUNTED_NAME.format(stem="song", count=FIRST_COUNT),
        ]

    def test_a_file_holding_no_project_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "notes.stp"
        path.write_text("not a project", encoding="utf-8")

        with pytest.raises(NotAValidArchiveError):
            loaded_projects((path,))

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            loaded_projects((tmp_path / "absent.stp",))


class TestUniqueName:
    def test_a_free_name_is_kept(self) -> None:
        assert unique_name("song", {"other"}) == "song"

    def test_a_taken_name_takes_the_lowest_free_count(self) -> None:
        taken: Set[str] = {"song", COUNTED_NAME.format(stem="song", count=FIRST_COUNT)}

        assert unique_name("song", taken) == COUNTED_NAME.format(stem="song", count=FIRST_COUNT + 1)
