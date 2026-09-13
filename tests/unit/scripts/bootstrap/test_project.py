import tomllib
from pathlib import Path

import pytest

from bootstrap.layout import repository_root
from bootstrap.project import NAMED_EXTRAS, NAMED_GROUPS, parse_project, read_project
from tests.suite.bootstrap import PROJECT_DOCUMENT, PROJECT_NAME, PROJECT_VERSION, write_project


class TestReadProject:
    def test_the_repository_states_every_name_the_scripts_install(self) -> None:
        project = read_project(repository_root())

        assert set(NAMED_EXTRAS) <= set(project.extras)
        assert set(NAMED_GROUPS) <= set(project.groups)
        assert (repository_root() / project.entry_script).is_file()
        assert all((repository_root() / "src" / package).is_dir() for package in project.packages)

    def test_the_facts_are_read_from_the_file(self, tmp_path: Path) -> None:
        project = read_project(write_project(tmp_path))

        assert project.name == PROJECT_NAME
        assert project.version == PROJECT_VERSION
        assert project.entry_module == f"{PROJECT_NAME}.__main__"
        assert project.entry_script == f"src/{PROJECT_NAME}/__main__.py"
        assert project.packages == (PROJECT_NAME, f"{PROJECT_NAME}_core")


class TestParseProject:
    def test_a_missing_extra_is_refused_by_name(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["project"]["optional-dependencies"]["gpu-cuda11"]

        with pytest.raises(SystemExit, match="gpu-cuda11"):
            parse_project(document)

    def test_a_missing_group_is_refused_by_name(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["dependency-groups"]["dev"]

        with pytest.raises(SystemExit, match="dev"):
            parse_project(document)

    def test_a_project_without_its_command_is_refused(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["project"]["scripts"]

        with pytest.raises(SystemExit, match=r"\[project.scripts\]"):
            parse_project(document)
