from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Final, Optional
from unittest.mock import patch

import pytest

from sampletones_shared.utils.system.programs import (
    LIBRARY_PATH,
    ORIGINAL_LIBRARY_PATH,
    locate_program,
    missing_program_message,
    program_environment,
    reader_environment,
)
from sampletones_shared.utils.system.system import System
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

BUNDLE_LIBRARIES: Final[str] = "/tmp/_MEI1234"
READER_LIBRARIES: Final[str] = "/opt/reader/lib"
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


class TestTheReaderEnvironment(BaseTestSuite):
    """A bundle hands a program the reader's own library path; any other run hands its variables on unchanged."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        environment: Dict[str, str]
        frozen: bool
        expected: Optional[str]

    test_cases = (
        TestCase(
            label="a bundle restores the reader's path",
            environment={LIBRARY_PATH: BUNDLE_LIBRARIES, ORIGINAL_LIBRARY_PATH: READER_LIBRARIES},
            frozen=True,
            expected=READER_LIBRARIES,
        ),
        TestCase(
            label="a bundle drops a path the reader never set",
            environment={LIBRARY_PATH: BUNDLE_LIBRARIES},
            frozen=True,
            expected=None,
        ),
        TestCase(
            label="a plain run keeps the reader's path",
            environment={LIBRARY_PATH: READER_LIBRARIES},
            frozen=False,
            expected=READER_LIBRARIES,
        ),
        TestCase(label="a plain run without a path sets none", environment={}, frozen=False, expected=None),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_library_path(self, test_case: TestCase) -> None:
        environment = reader_environment(test_case.environment, frozen=test_case.frozen)

        assert environment.get(LIBRARY_PATH) == test_case.expected

    def test_a_frozen_run_leaves_the_saved_path_behind(self) -> None:
        environment = reader_environment(
            {LIBRARY_PATH: BUNDLE_LIBRARIES, ORIGINAL_LIBRARY_PATH: READER_LIBRARIES},
            frozen=True,
        )

        assert ORIGINAL_LIBRARY_PATH not in environment

    def test_the_other_variables_pass_through(self) -> None:
        assert reader_environment({"HOME": "/home/reader"}, frozen=True) == {"HOME": "/home/reader"}


class TestProgramEnvironment:
    def test_a_run_from_a_checkout_hands_its_own_variables_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(LIBRARY_PATH, READER_LIBRARIES)

        assert program_environment()[LIBRARY_PATH] == READER_LIBRARIES

    def test_a_bundle_hands_the_reader_path_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(LIBRARY_PATH, BUNDLE_LIBRARIES)
        monkeypatch.setenv(ORIGINAL_LIBRARY_PATH, READER_LIBRARIES)
        monkeypatch.setattr("sys.frozen", True, raising=False)

        assert program_environment()[LIBRARY_PATH] == READER_LIBRARIES
