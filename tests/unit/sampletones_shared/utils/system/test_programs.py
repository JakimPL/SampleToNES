from pathlib import Path
from typing import Dict, Final
from unittest.mock import patch

import pytest

from sampletones_shared.utils.system.programs import (
    locate_program,
    missing_program_message,
)
from sampletones_shared.utils.system.system import System

HINTS: Final[Dict[System, str]] = {
    System.LINUX: "sudo apt install tool",
    System.MACOS: "brew install tool",
    System.WINDOWS: "install tool and add it to PATH",
}


class TestLocateProgram:
    """Where a program is installed, or nothing where this system carries none."""

    def test_an_installed_program_reports_where_it_is(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/tool"):
            assert locate_program("tool") == Path("/usr/bin/tool")

    def test_an_absent_program_reports_nothing(self) -> None:
        with patch("shutil.which", return_value=None):
            assert locate_program("tool") is None


class TestMissingProgramMessage:
    """What to report when a program the project reaches for is absent."""

    def test_the_message_names_the_program_its_purpose_and_the_install_command(self) -> None:
        with patch("platform.system", return_value="Linux"):
            message = missing_program_message("tool", "waves are rendered with tool", HINTS)

        assert message == "tool is missing: waves are rendered with tool (sudo apt install tool)"

    def test_every_system_names_its_own_command(self) -> None:
        with patch("platform.system", return_value="Darwin"):
            assert HINTS[System.MACOS] in missing_program_message("tool", "purpose", HINTS)

        with patch("platform.system", return_value="Windows"):
            assert HINTS[System.WINDOWS] in missing_program_message("tool", "purpose", HINTS)

    def test_a_system_with_no_hint_raises(self) -> None:
        with patch("platform.system", return_value="Linux"):
            with pytest.raises(KeyError):
                missing_program_message("tool", "purpose", {System.WINDOWS: "installer"})
