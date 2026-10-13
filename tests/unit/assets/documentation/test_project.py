from pathlib import Path

import pytest

from assets.documentation.project import ProjectFacts
from tests.unit.assets.documentation.conftest import ADDRESS, VERSION


class TestProjectFacts:
    def test_the_version_and_the_address_are_read(self, project: Path) -> None:
        assert ProjectFacts.read(project) == ProjectFacts(version=VERSION, documentation_address=ADDRESS)

    def test_a_project_naming_no_documentation_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "pyproject.toml"
        path.write_text('[project]\nversion = "1.0"\n', encoding="utf-8")

        with pytest.raises(KeyError):
            ProjectFacts.read(path)
