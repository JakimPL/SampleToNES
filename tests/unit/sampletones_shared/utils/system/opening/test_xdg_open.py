import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from sampletones_shared.utils.system.opening.xdg_open import (
    LIBRARY_PATH,
    ORIGINAL_LIBRARY_PATH,
    XDG_OPEN,
    XdgOpenFileOpener,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

POPEN = "sampletones_shared.utils.system.opening.xdg_open.subprocess.Popen"
BUNDLE_LIBRARIES = "/tmp/_MEI1234"
READER_LIBRARIES = "/opt/reader/lib"


class RecordedPopen:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, command: List[str], **options: Any) -> None:
        self.calls.append({"command": command, **options})


class TestTheChildEnvironment(BaseTestSuite):
    """A bundle hands the program the reader's own library path; a plain run hands it on unchanged."""

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
        opener = XdgOpenFileOpener(test_case.environment, frozen=test_case.frozen)
        environment = opener.child_environment()

        assert environment.get(LIBRARY_PATH) == test_case.expected
        assert ORIGINAL_LIBRARY_PATH not in environment or not test_case.frozen


class TestXdgOpenFileOpener:
    def test_the_file_is_handed_to_a_detached_xdg_open(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        popen = RecordedPopen()
        monkeypatch.setattr(POPEN, popen)
        page = tmp_path / "index.html"

        XdgOpenFileOpener({"HOME": "/home/reader"}, frozen=False).open(page)

        [call] = popen.calls
        assert call["command"] == [XDG_OPEN, str(page)]
        assert call["start_new_session"] is True
        assert call["env"] == {"HOME": "/home/reader"}
        assert call["stdout"] is subprocess.DEVNULL

    def test_a_missing_program_reaches_the_caller(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing(command: List[str], **options: Any) -> None:
            raise FileNotFoundError(command[0])

        monkeypatch.setattr(POPEN, missing)

        with pytest.raises(OSError):
            XdgOpenFileOpener({}, frozen=False).open(tmp_path / "index.html")
