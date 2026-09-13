import tomllib
from pathlib import Path

import pytest

from bootstrap.layout import SOURCE_DIRECTORY, repository_root
from bootstrap.project import (
    DEVELOPMENT_GROUP,
    GPU_CUDA11_EXTRA,
    NAMED_EXTRAS,
    NAMED_GROUPS,
    TAG_PREFIX,
    parse_project,
    read_project,
)
from tests.suite.bootstrap import PROJECT_DOCUMENT, PROJECT_NAME, PROJECT_VERSION, write_project


class TestReadProject:
    def test_the_repository_states_every_name_the_scripts_install(self) -> None:
        project = read_project(repository_root())

        assert set(NAMED_EXTRAS) <= set(project.extras)
        assert set(NAMED_GROUPS) <= set(project.groups)
        assert (repository_root() / project.entry_script).is_file()
        assert all((repository_root() / SOURCE_DIRECTORY / package).is_dir() for package in project.packages)

    def test_the_facts_are_read_from_the_file(self, tmp_path: Path) -> None:
        project = read_project(write_project(tmp_path))

        assert project.name == PROJECT_NAME
        assert project.version == PROJECT_VERSION
        assert project.entry_module == f"{PROJECT_NAME}.__main__"
        assert project.entry_script == f"{SOURCE_DIRECTORY}/{PROJECT_NAME}/__main__.py"
        assert project.packages == (PROJECT_NAME, f"{PROJECT_NAME}_core")
        assert project.tag == f"{TAG_PREFIX}{PROJECT_VERSION}"


class TestParseProject:
    def test_a_missing_extra_is_refused_by_name(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["project"]["optional-dependencies"][GPU_CUDA11_EXTRA]

        with pytest.raises(SystemExit, match=GPU_CUDA11_EXTRA):
            parse_project(document)

    def test_a_missing_group_is_refused_by_name(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["dependency-groups"][DEVELOPMENT_GROUP]

        with pytest.raises(SystemExit, match=DEVELOPMENT_GROUP):
            parse_project(document)

    def test_a_project_without_its_command_is_refused(self) -> None:
        document = tomllib.loads(PROJECT_DOCUMENT)
        del document["project"]["scripts"]

        with pytest.raises(SystemExit, match=r"\[project.scripts\]"):
            parse_project(document)
