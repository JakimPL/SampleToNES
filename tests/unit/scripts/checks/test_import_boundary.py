from pathlib import Path
from typing import Final

import pytest

from tests.suite.scripts import load_script
from tests.suite.source import write_module

check_import_boundary = load_script("checks/import_boundary.py")

APPLICATION: Final[str] = "sampletones_application"

VISUAL_IMPORT: Final[str] = "import dearpygui.dearpygui as dpg\n"
PLAIN_IMPORT: Final[str] = "from sampletones_core.project.project import Project\n"


class TestMain:
    def test_the_repository_holds_its_import_boundaries(self) -> None:
        assert check_import_boundary.main(["--all"]) == 0

    def test_a_forbidden_import_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = write_module(tmp_path / APPLICATION / "logic", "direct.py", VISUAL_IMPORT)

        exit_code = check_import_boundary.main(["--all", "--source", str(tmp_path)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"{path}:1" in error
        assert "dearpygui" in error

    def test_named_files_narrow_the_run_to_themselves(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_module(tmp_path / APPLICATION / "logic", "reported.py", VISUAL_IMPORT)
        clean = write_module(tmp_path / APPLICATION / "logic", "clean.py", PLAIN_IMPORT)

        assert check_import_boundary.main([str(clean), "--source", str(tmp_path)]) == 0
        assert capsys.readouterr().err == ""
