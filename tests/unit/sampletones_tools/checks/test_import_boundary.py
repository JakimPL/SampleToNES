from pathlib import Path
from typing import Final

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_tools.checks import import_boundary as check_import_boundary
from tests.suite.source import write_module

APPLICATION: Final[str] = "sampletones_application"

VISUAL_IMPORT: Final[str] = "import dearpygui.dearpygui as dpg\n"
PLAIN_IMPORT: Final[str] = "from sampletones_core.project.project import Project\n"
THIRD_PARTY_IMPORT: Final[str] = "import numpy\n"


class TestMain:
    def test_the_repository_holds_its_import_boundaries(self) -> None:
        assert dispatch(COMMANDS, ["check", "import-boundary", "--all"]) == 0

    def test_a_forbidden_import_is_reported_where_it_sits(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        path = write_module(tmp_path / APPLICATION / "logic", "direct.py", VISUAL_IMPORT)

        exit_code = dispatch(COMMANDS, ["check", "import-boundary", "--all", "--source", str(tmp_path)])

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"{path}:1" in error
        assert "dearpygui" in error

    def test_a_bootstrap_script_reaching_past_the_standard_library_is_reported(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_module(tmp_path / "src" / APPLICATION / "logic", "clean.py", PLAIN_IMPORT)
        path = write_module(tmp_path / "scripts", "bundle.py", THIRD_PARTY_IMPORT)

        exit_code = dispatch(
            COMMANDS,
            [
                "check",
                "import-boundary",
                "--all",
                "--source",
                str(tmp_path / "src"),
                "--scripts",
                str(tmp_path / "scripts"),
            ],
        )

        assert exit_code == 1
        error = capsys.readouterr().err
        assert f"{path}:1" in error
        assert "system interpreter" in error

    def test_named_files_narrow_the_run_to_themselves(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        write_module(tmp_path / APPLICATION / "logic", "reported.py", VISUAL_IMPORT)
        clean = write_module(tmp_path / APPLICATION / "logic", "clean.py", PLAIN_IMPORT)

        assert dispatch(COMMANDS, ["check", "import-boundary", str(clean), "--source", str(tmp_path)]) == 0
        assert capsys.readouterr().err == ""
