import tempfile
from pathlib import Path
from typing import Final

from automation.environment import (
    HOMES_VARIABLE,
    ScenarioFolders,
    child_environment,
    homes_root,
)

NODEID: Final[str] = "tests/screens/test_case.py::TestCase::test_it"
DISPLAY: Final[str] = ":9"


class TestWhereTheHomesGo:
    def test_the_homes_go_to_the_system_s_temporary_folder(self) -> None:
        assert homes_root({}) == Path(tempfile.gettempdir())

    def test_the_variable_moves_them(self) -> None:
        assert homes_root({HOMES_VARIABLE: "/work/homes"}) == Path("/work/homes")


class TestTheScenarioProcessEnvironment:
    """The process keeps the machine's temporary folder, whose short path its socket files fit in."""

    def test_the_temporary_folder_is_the_machine_s(self, tmp_path: Path) -> None:
        folders = ScenarioFolders.of(NODEID, homes=tmp_path / "homes", kept=tmp_path / "kept")

        environment = child_environment({"TMPDIR": "/tmp"}, folders, display=DISPLAY)

        assert environment["TMPDIR"] == "/tmp"
        assert environment["HOME"] == str(folders.home)

    def test_a_process_told_no_temporary_folder_is_told_none(self, tmp_path: Path) -> None:
        folders = ScenarioFolders.of(NODEID, homes=tmp_path / "homes", kept=tmp_path / "kept")

        environment = child_environment({}, folders, display=DISPLAY)

        assert "TMPDIR" not in environment
